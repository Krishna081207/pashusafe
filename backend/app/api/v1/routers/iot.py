from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import ensure_farm_access, farmer_or_admin, get_current_user, scoped_farm_ids
from app.db.session import get_db
from app.models import Animal, SensorReading, User
from app.models.enums import Role
from app.services import alert_service, health_monitor, iot_simulator

router = APIRouter(prefix="/iot", tags=["iot"])


@router.get("/readings")
def get_readings(
    animal_id: int,
    hours: int = 48,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    animal = db.get(Animal, animal_id)
    if not animal:
        raise HTTPException(404, "Animal not found")
    ensure_farm_access(user, animal.farm_id)
    iot_simulator.advance(db, [animal.id], hours_back=min(hours, 96))
    return {
        "animal_id": animal_id,
        "tag_id": animal.tag_id,
        "device_id": iot_simulator.device_for(animal),
        "fever_threshold_c": iot_simulator.FEVER_THRESHOLD_C,
        "readings": iot_simulator.readings_for(db, animal_id, hours=hours),
    }


@router.get("/latest")
def latest(
    farm_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Most recent reading per animal (dashboard tiles)."""
    allowed = scoped_farm_ids(user)
    stmt = select(Animal).where(Animal.status == "active")
    if allowed is not None:
        stmt = stmt.where(Animal.farm_id.in_(allowed or [-1]))
    elif farm_id is not None:
        stmt = stmt.where(Animal.farm_id == farm_id)
    animals = db.execute(stmt).scalars().all()
    if not animals:
        return []
    iot_simulator.advance(db, [a.id for a in animals], hours_back=6)
    out = []
    for animal in animals:
        reading = db.execute(
            select(SensorReading)
            .where(SensorReading.animal_id == animal.id)
            .order_by(SensorReading.recorded_at.desc())
            .limit(1)
        ).scalar_one_or_none()
        if reading:
            out.append(
                {
                    "animal_id": animal.id,
                    "tag_id": animal.tag_id,
                    "body_temp_c": reading.body_temp_c,
                    "activity_index": reading.activity_index,
                    "recorded_at": reading.recorded_at.isoformat() if reading.recorded_at else None,
                    "fever": reading.body_temp_c >= iot_simulator.FEVER_THRESHOLD_C,
                }
            )
    return out


@router.get("/devices")
def devices(farm_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    allowed = scoped_farm_ids(user)
    stmt = select(Animal)
    if allowed is not None:
        stmt = stmt.where(Animal.farm_id.in_(allowed or [-1]))
    elif farm_id is not None:
        stmt = stmt.where(Animal.farm_id == farm_id)
    animals = db.execute(stmt).scalars().all()
    return [
        {"device_id": iot_simulator.device_for(a), "animal_tag": a.tag_id, "scenario": a.scenario_tag or "healthy"}
        for a in animals
    ]


@router.get("/status/{animal_id}")
def health_status(
    animal_id: int,
    hours: int = 48,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Live health status: metrics + anomaly detection + who was notified."""
    animal = db.get(Animal, animal_id)
    if not animal:
        raise HTTPException(404, "Animal not found")
    ensure_farm_access(user, animal.farm_id)

    iot_simulator.advance(db, [animal.id], hours_back=min(hours, 96))
    created = health_monitor.run_detection(db, animal)
    db.commit()

    assessment = health_monitor.assess(db, animal, hours=24)

    owner = db.execute(
        select(User).where(User.farm_id == animal.farm_id, User.role == Role.farmer)
    ).scalars().first()
    vets = list(db.execute(select(User).where(User.role == Role.vet)).scalars().all())

    return {
        "animal_id": animal.id,
        "tag_id": animal.tag_id,
        "device_id": iot_simulator.device_for(animal),
        "scenario": animal.scenario_tag or "healthy",
        "assessment": (
            {
                "status": assessment.status,
                "current_temp_c": assessment.current_temp_c,
                "avg_temp_c": assessment.avg_temp_c,
                "peak_temp_c": assessment.peak_temp_c,
                "fever_hours": assessment.fever_hours,
                "activity_drop_pct": assessment.activity_drop_pct,
                "rumination_delta_pct": assessment.rumination_delta_pct,
                "readings_count": assessment.readings_count,
            }
            if assessment
            else None
        ),
        "notified": {
            "owner": {"full_name": owner.full_name if owner else None},
            "vets": [{"full_name": v.full_name} for v in vets],
        },
        "health_alerts": [
            alert_service.serialize(a) for a in health_monitor.open_health_alerts(db, animal)
        ],
        "new_alerts_raised": len(created),
    }


@router.post("/simulate-fever/{animal_id}")
def simulate_fever(
    animal_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(farmer_or_admin),
):
    """DEMO CONTROL: switch this animal's collar feed to the fever scenario.

    New sensor buckets immediately run hot; anomaly detection fires and alerts
    both the owner and the veterinary team within one poll cycle.
    """
    animal = db.get(Animal, animal_id)
    if not animal:
        raise HTTPException(404, "Animal not found")
    ensure_farm_access(user, animal.farm_id)

    animal.scenario_tag = "fever_outbreak"
    db.flush()
    iot_simulator.advance(db, [animal.id], hours_back=2)
    created = health_monitor.run_detection(db, animal)
    db.commit()
    return {
        "ok": True,
        "scenario": "fever_outbreak",
        "alerts_raised": [a.type.value for a in created],
        "message": (
            f"Fever simulation ON for {animal.tag_id}. Temperature will rise over "
            f"the next buckets; owner and vets notified."
        ),
    }


@router.post("/simulate-recovery/{animal_id}")
def simulate_recovery(
    animal_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(farmer_or_admin),
):
    """DEMO CONTROL: return the collar feed to normal and resolve alerts."""
    from app.models import Alert
    from app.models.enums import AlertType

    animal = db.get(Animal, animal_id)
    if not animal:
        raise HTTPException(404, "Animal not found")
    ensure_farm_access(user, animal.farm_id)

    animal.scenario_tag = "healthy"
    for a in health_monitor.open_health_alerts(db, animal):
        from app.utils.timeutil import utcnow

        a.resolved_at = utcnow()
    db.commit()
    return {"ok": True, "scenario": "healthy", "message": f"{animal.tag_id} recovered; alerts resolved."}
