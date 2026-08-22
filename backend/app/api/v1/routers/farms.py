from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import ensure_farm_access, get_current_user, scoped_farm_ids
from app.db.session import get_db
from app.models import Animal, Farm, User
from app.services import alert_service
from app.services.mrl_engine import farm_compliance

router = APIRouter(prefix="/farms", tags=["farms"])


@router.get("")
def list_farms(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    allowed = scoped_farm_ids(user)
    stmt = select(Farm).order_by(Farm.id)
    if allowed is not None:
        stmt = stmt.where(Farm.id.in_(allowed))
    farms = db.execute(stmt).scalars().all()
    counts = dict(
        db.execute(
            select(Animal.farm_id, func.count()).group_by(Animal.farm_id)
        ).all()
    )
    return [
        {
            "id": f.id, "name": f.name, "village": f.village, "district": f.district,
            "state": f.state, "pincode": f.pincode,
            "animal_count": counts.get(f.id, 0),
        }
        for f in farms
    ]


@router.get("/{farm_id}")
def get_farm(farm_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ensure_farm_access(user, farm_id)
    farm = db.get(Farm, farm_id)
    if not farm:
        raise HTTPException(404, "Farm not found")
    compliance = farm_compliance(db, farm_id)
    under = sum(1 for c in compliance if c["under_withdrawal"])
    return {
        "id": farm.id, "name": farm.name, "village": farm.village, "district": farm.district,
        "state": farm.state, "pincode": farm.pincode,
        "animal_count": len(compliance),
        "under_withdrawal_count": under,
        "compliance": compliance,
    }
