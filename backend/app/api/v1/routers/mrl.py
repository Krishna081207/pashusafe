from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import ensure_farm_access, get_current_user, scoped_farm_ids
from app.db.session import get_db
from app.models import Animal, Farm, User
from app.services.mrl_engine import animal_compliance, farm_compliance, violation_report

router = APIRouter(prefix="/mrl", tags=["mrl"])


@router.get("/status/overview")
def status_overview(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Per-farm rollup (animals + under-withdrawal counts) for every farm the
    caller may see -- powers vet/regulator dashboards."""
    allowed = scoped_farm_ids(user)
    stmt = select(Farm).order_by(Farm.id)
    if allowed is not None:
        stmt = stmt.where(Farm.id.in_(allowed or [-1]))
    farms = db.execute(stmt).scalars().all()

    out = []
    for f in farms:
        rows = farm_compliance(db, f.id)
        out.append(
            {
                "farm_id": f.id,
                "name": f.name,
                "district": f.district,
                "state": f.state,
                "animal_count": len(rows),
                "under_withdrawal": sum(1 for r in rows if r["under_withdrawal"]),
                "clear_today": sum(1 for r in rows if r["overall"] == "CLEAR_TODAY"),
            }
        )
    return out


@router.get("/status/farm/{farm_id}")
def farm_status(farm_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Traffic-light compliance snapshot for every active animal on a farm."""
    ensure_farm_access(user, farm_id)
    rows = farm_compliance(db, farm_id)
    return {
        "farm_id": farm_id,
        "animals": rows,
        "counts": {
            "withdrawal_active": sum(1 for r in rows if r["overall"] == "WITHDRAWAL_ACTIVE"),
            "clear_today": sum(1 for r in rows if r["overall"] == "CLEAR_TODAY"),
            "clear": sum(1 for r in rows if r["overall"] == "CLEAR"),
        },
    }


@router.get("/status/animal/{animal_id}")
def animal_status(animal_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    animal = db.get(Animal, animal_id)
    if not animal:
        raise HTTPException(404, "Animal not found")
    ensure_farm_access(user, animal.farm_id)
    return animal_compliance(db, animal)


@router.get("/violations")
def list_violations(
    farm_id: int | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    allowed = scoped_farm_ids(user)
    ids = allowed if allowed is not None else ([farm_id] if farm_id else None)
    return violation_report(db, ids, limit=limit)
