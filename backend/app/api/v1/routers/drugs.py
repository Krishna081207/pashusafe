from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models import Drug, User
from app.schemas import DrugOut

router = APIRouter(prefix="/drugs", tags=["drugs"])


@router.get("", response_model=list[DrugOut])
def list_drugs(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    drugs = db.execute(select(Drug).order_by(Drug.generic_name)).scalars().all()
    return [
        DrugOut(
            id=d.id,
            generic_name=d.generic_name,
            active_ingredient=d.active_ingredient,
            drug_class=d.drug_class,
            aware_class=d.aware_class.value,
            prohibited_in_food_animals=d.prohibited_in_food_animals,
            prohibited_in_lactating_animals=d.prohibited_in_lactating_animals,
            notes=d.notes,
            rules=[
                {
                    "id": r.id,
                    "drug_id": r.drug_id,
                    "species": r.species,
                    "withdrawal_milk_days": r.withdrawal_milk_days,
                    "withdrawal_meat_days": r.withdrawal_meat_days,
                    "withdrawal_eggs_days": r.withdrawal_eggs_days,
                    "mrl_milk_ug_kg": r.mrl_milk_ug_kg,
                    "mrl_meat_ug_kg": r.mrl_meat_ug_kg,
                    "mrl_eggs_ug_kg": r.mrl_eggs_ug_kg,
                    "source": r.source,
                }
                for r in d.rules
            ],
        )
        for d in drugs
    ]
