from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, regulator_or_admin, scoped_farm_ids
from app.db.session import get_db
from app.models import Animal, Drug, ResidueTest, SaleEvent, User, WithdrawalPeriod
from app.models import Administration
from app.models.enums import (
    AlertSeverity,
    AlertType,
    LedgerEventType,
    ResidueResult,
    SaleProduct,
    Tissue,
    WithdrawalStatus,
)
from app.schemas import ResidueTestIn
from app.services import alert_service, ledger_service

router = APIRouter(prefix="/residue-tests", tags=["residue-tests"])


@router.post("", status_code=201)
def create_residue_test(
    payload: ResidueTestIn,
    db: Session = Depends(get_db),
    user: User = Depends(regulator_or_admin),
):
    """Regulator records a lab result.

    fail  -> confirms the violation (alert upgraded to MRL_VIOLATION_CONFIRMED).
    pass  -> if the animal is still inside a theoretical withdrawal window for
             this drug/tissue, the window is cleared early with evidence.
    """
    drug = db.get(Drug, payload.drug_id)
    if not drug:
        raise HTTPException(404, "Drug not found")
    animal = db.get(Animal, payload.animal_id) if payload.animal_id else None
    sale = db.get(SaleEvent, payload.sale_event_id) if payload.sale_event_id else None
    farm_id = animal.farm_id if animal else (sale.farm_id if sale else None)
    if farm_id is None:
        raise HTTPException(422, "Residue test must reference an animal or a sale event")

    mrl_ref = _mrl_reference(db, drug.id, animal.species.value, payload.sample_type) if animal else None
    measured = payload.measured_residue_ug_kg
    result = ResidueResult(payload.result)

    test = ResidueTest(
        sample_type=payload.sample_type,
        animal_id=animal.id if animal else None,
        sale_event_id=sale.id if sale else None,
        drug_id=drug.id,
        method=payload.method,
        measured_residue_ug_kg=measured,
        mrl_reference_ug_kg=mrl_ref,
        result=result,
        notes=payload.notes,
    )
    db.add(test)
    db.flush()

    alerts_raised = []
    if result == ResidueResult.fail:
        alert_service.create_alert(
            db,
            farm_id=farm_id,
            animal_id=animal.id if animal else None,
            type_=AlertType.MRL_VIOLATION_CONFIRMED,
            severity=AlertSeverity.critical,
            title=f"LAB CONFIRMED residue violation: {drug.generic_name}",
            message=(
                f"Laboratory {payload.method} test detected {drug.generic_name} at "
                f"{measured if measured is not None else '?'} ug/kg vs MRL "
                f"{mrl_ref if mrl_ref is not None else '?'} ug/kg "
                f"({payload.sample_type.value}). Product must be quarantined; "
                f"further enforcement per FSSAI protocol."
            ),
            related_type="residue_test",
            related_id=test.id,
        )
        if sale and not sale.is_violation:
            sale.is_violation = True
        alerts_raised.append("MRL_VIOLATION_CONFIRMED")
    elif result == ResidueResult.pass_ and animal is not None:
        cleared = _early_clear(db, animal, drug.id, payload.sample_type)
        if cleared:
            alert_service.create_alert(
                db,
                farm_id=farm_id,
                animal_id=animal.id,
                type_=AlertType.MRL_VIOLATION_CONFIRMED,
                severity=AlertSeverity.info,
                title=f"Evidence-based early clearance for {animal.tag_id}",
                message=(
                    f"{payload.method} test PASSED ({measured} ug/kg vs MRL "
                    f"{mrl_ref}) -- {len(cleared)} withdrawal window(s) marked cleared "
                    f"with laboratory evidence."
                ),
                related_type="residue_test",
                related_id=test.id,
            )
            alerts_raised.append("EARLY_CLEARANCE_EVIDENCED")

    ledger_service.append_event(
        db,
        LedgerEventType.residue_test,
        test.id,
        {
            "residue_test_id": test.id,
            "animal_tag": animal.tag_id if animal else None,
            "drug": drug.generic_name,
            "sample_type": payload.sample_type.value,
            "method": payload.method,
            "measured_ug_kg": measured,
            "mrl_reference_ug_kg": mrl_ref,
            "result": result.value,
            "lab": "State Vet Lab",
        },
        actor_user_id=user.id,
    )
    db.commit()
    return {"id": test.id, "alerts_raised": alerts_raised}


def _mrl_reference(db: Session, drug_id: int, species_value: str, sample) -> float | None:
    from app.models import DrugSpeciesRule
    from app.models.enums import Species

    try:
        species = Species(species_value)
    except ValueError:
        return None
    rule = db.execute(
        select(DrugSpeciesRule).where(
            DrugSpeciesRule.drug_id == drug_id, DrugSpeciesRule.species == species
        )
    ).scalar_one_or_none()
    if rule is None:
        return None
    return {
        SaleProduct.milk: rule.mrl_milk_ug_kg,
        SaleProduct.meat: rule.mrl_meat_ug_kg,
        SaleProduct.live_animal: rule.mrl_meat_ug_kg,
        SaleProduct.eggs: rule.mrl_eggs_ug_kg,
    }.get(sample)


def _early_clear(db: Session, animal: Animal, drug_id: int, sample) -> list[int]:
    """Flip active windows for (animal, drug-of-test, tissue-of-sample) to cleared."""
    tissue_value = {
        SaleProduct.milk: Tissue.milk,
        SaleProduct.meat: Tissue.meat,
        SaleProduct.live_animal: Tissue.meat,
        SaleProduct.eggs: Tissue.eggs,
    }.get(sample)
    if tissue_value is None:
        return []
    stmt = (
        select(WithdrawalPeriod)
        .join(Administration, WithdrawalPeriod.administration_id == Administration.id)
        .where(
            Administration.animal_id == animal.id,
            Administration.drug_id == drug_id,
            WithdrawalPeriod.tissue == tissue_value,
            WithdrawalPeriod.status == WithdrawalStatus.active,
        )
    )
    rows = db.execute(stmt).scalars().all()
    cleared_ids: list[int] = []
    for wp in rows:
        wp.status = WithdrawalStatus.cleared
        cleared_ids.append(wp.id)
    db.flush()
    return cleared_ids


@router.get("")
def list_residue_tests(
    limit: int = 100,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = (
        select(ResidueTest, Animal, Drug)
        .outerjoin(Animal, ResidueTest.animal_id == Animal.id)
        .join(Drug, ResidueTest.drug_id == Drug.id)
        .order_by(ResidueTest.tested_at.desc())
        .limit(limit)
    )
    allowed = scoped_farm_ids(user)
    if allowed is not None:
        stmt = stmt.where(Animal.farm_id.in_(allowed or [-1]))
    rows = db.execute(stmt).all()
    return [
        {
            "id": t.id,
            "animal_tag": a.tag_id if a else None,
            "farm_id": a.farm_id if a else None,
            "drug_name": d.generic_name,
            "sample_type": t.sample_type.value,
            "method": t.method,
            "measured_residue_ug_kg": t.measured_residue_ug_kg,
            "mrl_reference_ug_kg": t.mrl_reference_ug_kg,
            "result": t.result.value,
            "tested_at": t.tested_at.isoformat() if t.tested_at else None,
        }
        for t, a, d in rows
    ]
