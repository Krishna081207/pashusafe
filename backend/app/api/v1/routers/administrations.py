from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import ensure_farm_access, get_current_user, scoped_farm_ids, staff
from app.db.session import get_db
from app.models import Administration, Animal, Drug, User
from app.models.enums import (
    AlertSeverity,
    AlertType,
    LedgerEventType,
    ProductionStatus,
    Species,
)
from app.schemas import AdministrationIn
from app.services import alert_service, ledger_service, mrl_engine
from app.utils.timeutil import utcnow as _utcnow

router = APIRouter(prefix="/administrations", tags=["administrations"])


@router.post("", status_code=201)
def create_administration(
    payload: AdministrationIn,
    db: Session = Depends(get_db),
    user: User = Depends(staff),
):
    """Record a treatment course.

    Side effects (single transaction): withdrawal-period rows materialized,
    prohibited-drug checks (R2), tamper-evident ledger entry appended.
    """
    animal = db.get(Animal, payload.animal_id)
    if not animal:
        raise HTTPException(404, "Animal not found")
    ensure_farm_access(user, animal.farm_id)
    drug = db.get(Drug, payload.drug_id)
    if not drug:
        raise HTTPException(404, "Drug not found")

    started_at = _utcnow() if payload.started_at is None else payload.started_at
    try:
        admin, rows = mrl_engine.record_administration(
            db,
            animal=animal,
            drug=drug,
            started_at=started_at,
            course_days=payload.course_days,
            dose_amount=payload.dose_amount,
            route=payload.route,
            prescription_id=payload.prescription_id,
            administered_by_user_id=user.id,
            batch_number=payload.batch_number,
            cost_inr=payload.cost_inr,
            notes=payload.notes,
        )
    except ValueError as e:
        raise HTTPException(422, str(e))

    # R2: prohibited-drug stewardship guard
    alerts_created: list[dict] = []
    if drug.prohibited_in_food_animals:
        a = alert_service.create_alert(
            db,
            farm_id=animal.farm_id,
            animal_id=animal.id,
            type_=AlertType.PROHIBITED_DRUG_USED,
            severity=AlertSeverity.critical,
            title=f"PROHIBITED drug used on {animal.tag_id}: {drug.generic_name}",
            message=(
                f"{drug.generic_name} ({drug.drug_class}) is banned in food-producing "
                f"animals but was recorded on {animal.tag_id}. Regulatory escalation "
                f"required; animals must not enter the food chain."
            ),
            related_type="administration",
            related_id=admin.id,
        )
        alerts_created.append({"type": a.type.value, "severity": a.severity.value})
    elif drug.prohibited_in_lactating_animals and animal.production_status == ProductionStatus.lactating:
        a = alert_service.create_alert(
            db,
            farm_id=animal.farm_id,
            animal_id=animal.id,
            type_=AlertType.PROHIBITED_DRUG_USED,
            severity=AlertSeverity.critical,
            title=f"{drug.generic_name} not permitted in lactating {animal.tag_id}",
            message=(
                f"{drug.generic_name} is prohibited in lactating animals. Milk from "
                f"{animal.tag_id} must be discarded until cleared by regulatory guidance."
            ),
            related_type="administration",
            related_id=admin.id,
        )
        alerts_created.append({"type": a.type.value, "severity": a.severity.value})

    ledger_service.append_event(
        db,
        LedgerEventType.administration,
        admin.id,
        {
            "animal_tag": animal.tag_id,
            "qr_code": animal.qr_code,
            "drug": drug.generic_name,
            "aware_class": drug.aware_class.value,
            "dose_mg_kg": admin.dose_amount,
            "route": admin.route.value,
            "course_days": admin.course_days,
            "started_at": admin.started_at.isoformat(),
            "last_dose_at": admin.last_dose_at.isoformat(),
            "supervised": admin.prescription_id is not None,
            "withdrawal_clears_at": {
                r.tissue.value: r.clears_at.isoformat() for r in rows
            },
        },
        actor_user_id=user.id,
    )
    db.commit()

    return {
        **mrl_engine.animal_compliance(db, animal),
        "administration_id": admin.id,
        "alerts_raised": alerts_created,
    }


@router.get("")
def list_administrations(
    animal_id: int | None = None,
    farm_id: int | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = (
        select(Administration, Animal, Drug)
        .join(Animal, Administration.animal_id == Animal.id)
        .join(Drug, Administration.drug_id == Drug.id)
        .order_by(Administration.started_at.desc())
        .limit(limit)
    )
    allowed = scoped_farm_ids(user)
    if allowed is not None:
        stmt = stmt.where(Animal.farm_id.in_(allowed or [-1]))
    else:
        if farm_id is not None:
            stmt = stmt.where(Animal.farm_id == farm_id)
        if animal_id is not None:
            stmt = stmt.where(Administration.animal_id == animal_id)
    rows = db.execute(stmt).all()
    return [
        {
            "id": adm.id,
            "animal_tag": animal.tag_id,
            "farm_id": animal.farm_id,
            "drug_name": drug.generic_name,
            "aware_class": drug.aware_class.value,
            "supervised": adm.prescription_id is not None,
            "dose_amount": adm.dose_amount,
            "route": adm.route.value,
            "course_days": adm.course_days,
            "started_at": adm.started_at.isoformat() if adm.started_at else None,
            "last_dose_at": adm.last_dose_at.isoformat() if adm.last_dose_at else None,
        }
        for adm, animal, drug in rows
    ]
