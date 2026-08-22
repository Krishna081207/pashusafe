from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import ensure_farm_access, get_current_user, scoped_farm_ids
from app.db.session import get_db
from app.models import Alert, User
from app.services import alert_service
from app.utils.timeutil import utcnow

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("")
def list_alerts(
    farm_id: int | None = None,
    unresolved_only: bool = True,
    limit: int = 100,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    allowed = scoped_farm_ids(user)
    alert_service.refresh_lazy_alerts(db, allowed)  # lazy R5 + sensor checks
    db.commit()

    stmt = select(Alert).order_by(Alert.created_at.desc()).limit(limit)
    if allowed is not None:
        stmt = stmt.where(Alert.farm_id.in_(allowed or [-1]))
    elif farm_id is not None:
        stmt = stmt.where(Alert.farm_id == farm_id)
    if unresolved_only:
        stmt = stmt.where(Alert.resolved_at.is_(None))
    alerts = db.execute(stmt).scalars().all()

    order = {"critical": 0, "warning": 1, "info": 2}
    items = [alert_service.serialize(a) for a in alerts]
    items.sort(
        key=lambda a: (order.get(a["severity"], 3), a["created_at"] or ""),
        reverse=False,
    )
    return items


@router.patch("/{alert_id}/read")
def mark_read(alert_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(404, "Alert not found")
    ensure_farm_access(user, alert.farm_id)
    alert.is_read = True
    db.commit()
    return {"ok": True}


@router.post("/{alert_id}/resolve")
def resolve(alert_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(404, "Alert not found")
    ensure_farm_access(user, alert.farm_id)
    alert.resolved_at = utcnow()
    db.commit()
    return {"ok": True}
