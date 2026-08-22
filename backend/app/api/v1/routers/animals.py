from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import (
    ensure_farm_access,
    farmer_or_admin,
    get_current_user,
    require_roles,
    scoped_farm_ids,
)
from app.db.session import get_db
from app.models import Administration, Animal, Drug, ResidueTest, SaleEvent, User
from app.models.enums import LedgerEventType
from app.schemas import AnimalIn, AnimalUpdate
from app.services import alert_service, ledger_service
from app.services.mrl_engine import animal_compliance

router = APIRouter(prefix="/animals", tags=["animals"])


@router.get("")
def list_animals(
    farm_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    allowed = scoped_farm_ids(user)
    stmt = select(Animal).order_by(Animal.tag_id)
    if allowed is not None:
        if not allowed:
            return []
        stmt = stmt.where(Animal.farm_id.in_(allowed))
    elif farm_id is not None:
        stmt = stmt.where(Animal.farm_id == farm_id)
    animals = db.execute(stmt).scalars().all()
    return [
        {
            "id": a.id,
            "farm_id": a.farm_id,
            "tag_id": a.tag_id,
            "species": a.species.value,
            "breed": a.breed,
            "sex": a.sex.value,
            "production_status": a.production_status.value,
            "weight_kg": a.weight_kg,
            "status": a.status.value,
            "qr_code": a.qr_code,
        }
        for a in animals
    ]


@router.post("", status_code=201)
def create_animal(
    payload: AnimalIn,
    db: Session = Depends(get_db),
    user: User = Depends(farmer_or_admin),
):
    if user.farm_id is None:
        raise HTTPException(400, "User has no farm")
    dup = db.execute(
        select(Animal).where(
            Animal.farm_id == user.farm_id, Animal.tag_id == payload.tag_id
        )
    ).scalar_one_or_none()
    if dup:
        raise HTTPException(409, f"Tag '{payload.tag_id}' already exists on this farm")
    animal = Animal(farm_id=user.farm_id, **payload.model_dump())
    db.add(animal)
    db.flush()
    ledger_service.append_event(
        db,
        LedgerEventType.animal_registered,
        animal.id,
        {
            "tag_id": animal.tag_id,
            "species": animal.species.value,
            "breed": animal.breed,
            "farm_id": animal.farm_id,
        },
        actor_user_id=user.id,
    )
    db.commit()
    return {"id": animal.id, "tag_id": animal.tag_id, "qr_code": animal.qr_code}


@router.get("/{animal_id}")
def animal_dossier(animal_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    animal = db.get(Animal, animal_id)
    if not animal:
        raise HTTPException(404, "Animal not found")
    ensure_farm_access(user, animal.farm_id)

    admins = list(
        db.execute(
            select(Administration)
            .where(Administration.animal_id == animal.id)
            .order_by(Administration.started_at.desc())
            .limit(25)
        ).scalars().all()
    )
    drug_ids = {a.drug_id for a in admins}
    drugs = {
        d.id: d
        for d in db.execute(select(Drug).where(Drug.id.in_(drug_ids))).scalars().all()
    } if drug_ids else {}

    sales = list(
        db.execute(
            select(SaleEvent).where(SaleEvent.animal_id == animal.id)
            .order_by(SaleEvent.occurred_at.desc()).limit(15)
        ).scalars().all()
    )
    tests = list(
        db.execute(
            select(ResidueTest).where(ResidueTest.animal_id == animal.id)
            .order_by(ResidueTest.tested_at.desc()).limit(10)
        ).scalars().all()
    )

    return {
        **animal_compliance(db, animal),
        "qr_code": animal.qr_code,
        "weight_kg": animal.weight_kg,
        "status": animal.status.value,
        "administrations": [
            {
                "id": a.id,
                "drug_name": drugs[a.drug_id].generic_name if a.drug_id in drugs else "?",
                "aware_class": drugs[a.drug_id].aware_class.value if a.drug_id in drugs else None,
                "supervised": a.prescription_id is not None,
                "dose_amount": a.dose_amount,
                "route": a.route.value,
                "course_days": a.course_days,
                "started_at": a.started_at.isoformat() if a.started_at else None,
                "last_dose_at": a.last_dose_at.isoformat() if a.last_dose_at else None,
            }
            for a in admins
        ],
        "sales": [
            {
                "id": s.id,
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
                "id": t.id,
                "drug_id": t.drug_id,
                "sample_type": t.sample_type.value,
                "result": t.result.value,
                "measured_residue_ug_kg": t.measured_residue_ug_kg,
                "mrl_reference_ug_kg": t.mrl_reference_ug_kg,
                "tested_at": t.tested_at.isoformat() if t.tested_at else None,
            }
            for t in tests
        ],
    }


@router.patch("/{animal_id}")
def update_animal(
    animal_id: int,
    payload: AnimalUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(farmer_or_admin),
):
    animal = db.get(Animal, animal_id)
    if not animal:
        raise HTTPException(404, "Animal not found")
    ensure_farm_access(user, animal.farm_id)
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(animal, k, v)
    db.commit()
    return animal_compliance(db, animal)


@router.post("/check-scope/{target_farm_id}")
def check_scope(target_farm_id: int, user: User = Depends(require_roles())):
    """Smoke-test helper: 403 unless caller may read target farm."""
    ensure_farm_access(user, target_farm_id)
    return {"ok": True}
