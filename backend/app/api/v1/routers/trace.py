"""Public QR traceability. No auth on /trace/public/{qr_code} -- this is the
page a buyer sees after scanning the QR printed on the animal's card."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import farmer_or_admin, get_current_user
from app.db.session import get_db
from app.models import Administration, Animal, Drug, ResidueTest, SaleEvent, User
from app.services import ledger_service

router = APIRouter(prefix="/trace", tags=["trace"])


@router.get("/qr/{animal_id}")
def qr_for_animal(
    animal_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(farmer_or_admin),
):
    animal = db.get(Animal, animal_id)
    if not animal:
        raise HTTPException(404, "Animal not found")
    return {
        "animal_id": animal.id,
        "tag_id": animal.tag_id,
        "qr_code": animal.qr_code,
        "trace_url": f"/trace/{animal.qr_code}",
    }


def _public_history(db: Session, animal: Animal) -> dict:
    admins = list(
        db.execute(
            select(Administration)
            .where(Administration.animal_id == animal.id)
            .order_by(Administration.started_at.asc())
        ).scalars().all()
    )
    drug_ids = {a.drug_id for a in admins}
    drugs = (
        {d.id: d for d in db.execute(select(Drug).where(Drug.id.in_(drug_ids))).scalars().all()}
        if drug_ids else {}
    )
    sales = list(
        db.execute(
            select(SaleEvent).where(SaleEvent.animal_id == animal.id)
            .order_by(SaleEvent.occurred_at.asc())
        ).scalars().all()
    )
    tests = list(
        db.execute(
            select(ResidueTest).where(ResidueTest.animal_id == animal.id)
            .order_by(ResidueTest.tested_at.asc())
        ).scalars().all()
    )
    return {
        "tag_id": animal.tag_id,
        "species": animal.species.value if hasattr(animal.species, "value") else str(animal.species),
        "breed": animal.breed,
        "production_status": animal.production_status.value,
        "medicine_history": [
            {
                "drug_name": drugs[a.drug_id].generic_name if a.drug_id in drugs else "?",
                "aware_class": drugs[a.drug_id].aware_class.value if a.drug_id in drugs else None,
                "dose_mg_kg": a.dose_amount,
                "route": a.route.value,
                "course_days": a.course_days,
                "started_at": a.started_at.isoformat() if a.started_at else None,
                "supervised": a.prescription_id is not None,
            }
            for a in admins
        ],
        "sale_history": [
            {
                "product_type": s.product_type.value,
                "quantity": s.quantity,
                "unit": s.unit,
                "is_violation": s.is_violation,
                "occurred_at": s.occurred_at.isoformat() if s.occurred_at else None,
            }
            for s in sales
        ],
        "residue_tests": [
            {
                "drug_name": drugs.get(t.drug_id).generic_name if t.drug_id in drugs else None,
                "result": t.result.value,
                "method": t.method,
                "measured_ug_kg": t.measured_residue_ug_kg,
                "mrl_reference_ug_kg": t.mrl_reference_ug_kg,
                "tested_at": t.tested_at.isoformat() if t.tested_at else None,
            }
            for t in tests
        ],
        "violation_count": sum(1 for s in sales if s.is_violation),
    }


@router.get("/public/{qr_code}")
def public_trace(qr_code: str, db: Session = Depends(get_db)):
    """Fully public supply-chain view + live ledger integrity badge."""
    animal = db.execute(
        select(Animal).where(Animal.qr_code == qr_code)
    ).scalar_one_or_none()
    if not animal:
        raise HTTPException(404, "Unknown QR code")

    history = _public_history(db, animal)
    verify = ledger_service.verify_chain(db)

    # Ledger entries that concern this animal (payload contains its qr/tag).
    entries = ledger_service.recent_entries(db, limit=500)
    mine = [
        {"seq": e.seq, "event_type": e.event_type.value, "hash": e.hash[:16] + "...",
         "recorded_at": e.recorded_at.isoformat() if e.recorded_at else None}
        for e in reversed(entries)
        if animal.qr_code in (e.payload_json or "") or animal.tag_id in (e.payload_json or "")
    ]

    return {**history, "ledger_integrity": verify["valid"], "ledger_events": mine[-20:]}
