from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, scoped_farm_ids, vet_or_admin
from app.db.session import get_db
from app.models import Animal, Drug, Prescription, User
from app.models.enums import LedgerEventType
from app.schemas import PrescriptionIn
from app.services import ledger_service

router = APIRouter(prefix="/prescriptions", tags=["prescriptions"])


@router.post("", status_code=201)
def create_prescription(
    payload: PrescriptionIn,
    db: Session = Depends(get_db),
    user: User = Depends(vet_or_admin),
):
    animal = db.get(Animal, payload.animal_id)
    if not animal:
        raise HTTPException(404, "Animal not found")
    drug = db.get(Drug, payload.drug_id)
    if not drug:
        raise HTTPException(404, "Drug not found")
    rx = Prescription(vet_id=user.id, **payload.model_dump())
    db.add(rx)
    db.flush()
    ledger_service.append_event(
        db,
        LedgerEventType.animal_registered,  # prescription rides the animal's chain
        animal.id,
        {
            "kind": "prescription",
            "prescription_id": rx.id,
            "drug": drug.generic_name,
            "dose_mg_kg": rx.dose_amount,
            "duration_days": rx.duration_days,
            "diagnosis": rx.diagnosis,
            "vet_id": user.id,
        },
        actor_user_id=user.id,
    )
    db.commit()
    return {"id": rx.id, "animal_id": rx.animal_id}


@router.get("")
def list_prescriptions(
    animal_id: int | None = None,
    farm_id: int | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = (
        select(Prescription, Animal, Drug)
        .join(Animal, Prescription.animal_id == Animal.id)
        .join(Drug, Prescription.drug_id == Drug.id)
        .order_by(Prescription.issued_at.desc())
        .limit(limit)
    )
    allowed = scoped_farm_ids(user)
    if allowed is not None:
        stmt = stmt.where(Animal.farm_id.in_(allowed or [-1]))
    else:
        if farm_id is not None:
            stmt = stmt.where(Animal.farm_id == farm_id)
        if animal_id is not None:
            stmt = stmt.where(Prescription.animal_id == animal_id)
    rows = db.execute(stmt).all()
    return [
        {
            "id": rx.id,
            "animal_tag": animal.tag_id,
            "farm_id": animal.farm_id,
            "drug_name": drug.generic_name,
            "aware_class": drug.aware_class.value,
            "diagnosis": rx.diagnosis,
            "dose_amount": rx.dose_amount,
            "route": rx.route.value,
            "frequency_per_day": rx.frequency_per_day,
            "duration_days": rx.duration_days,
            "issued_at": rx.issued_at.isoformat() if rx.issued_at else None,
        }
        for rx, animal, drug in rows
    ]
