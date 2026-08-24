"""IoT sensor installation visits.

Farmers request a preferred date + slot; an admin confirms the final slot and
assigns the installation official, or reschedules. Entering `scheduled` raises
an INSTALL_UPDATE alert visible only to the farm's farmer.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import (
    any_authenticated,
    ensure_farm_access,
    farmer_or_admin,
    require_roles,
    scoped_farm_ids,
)
from app.db.session import get_db
from app.models import SensorInstallVisit, User
from app.models.enums import AlertAudience, AlertSeverity, AlertType, Role, VisitStatus
from app.schemas import InstallVisitRequestIn, InstallVisitUpdateIn
from app.services import alert_service
from app.utils.timeutil import ensure_aware, ist_str, utcnow

router = APIRouter(prefix="/installs", tags=["installs"])

_OPEN_STATUSES = (VisitStatus.requested, VisitStatus.scheduled)


def _serialize(v: SensorInstallVisit) -> dict:
    scheduled = ensure_aware(v.scheduled_at) if v.scheduled_at else None
    completed = ensure_aware(v.completed_at) if v.completed_at else None
    return {
        "id": v.id,
        "farm_id": v.farm_id,
        "farm_name": v.farm.name if v.farm else None,
        "status": v.status.value,
        "preferred_date": v.preferred_date.isoformat(),
        "preferred_date_display": v.preferred_date.strftime("%d %b %Y"),
        "preferred_slot": v.preferred_slot.value,
        "notes": v.notes,
        "scheduled_at": scheduled.isoformat() if scheduled else None,
        "scheduled_at_display": ist_str(scheduled) if scheduled else None,
        "official_name": v.official_name,
        "official_phone": v.official_phone,
        "completed_at_display": ist_str(completed) if completed else None,
        "cancel_reason": v.cancel_reason,
        "created_at": ensure_aware(v.created_at).isoformat(),
    }


@router.post("")
def request_visit(
    payload: InstallVisitRequestIn,
    db: Session = Depends(get_db),
    user: User = Depends(farmer_or_admin),
):
    if user.farm_id is None:
        raise HTTPException(400, "No farm linked to this account")
    open_visit = db.execute(
        select(SensorInstallVisit).where(
            SensorInstallVisit.farm_id == user.farm_id,
            SensorInstallVisit.status.in_(_OPEN_STATUSES),
        )
    ).scalar_one_or_none()
    if open_visit:
        raise HTTPException(409, f"Visit #{open_visit.id} is already {open_visit.status.value}")
    visit = SensorInstallVisit(
        farm_id=user.farm_id,
        requested_by_user_id=user.id,
        preferred_date=payload.preferred_date,
        preferred_slot=payload.preferred_slot,
        notes=payload.notes,
    )
    db.add(visit)
    db.commit()
    db.refresh(visit)
    return _serialize(visit)


@router.get("")
def list_visits(
    status: VisitStatus | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(any_authenticated),
):
    allowed = scoped_farm_ids(user)
    stmt = select(SensorInstallVisit).order_by(SensorInstallVisit.created_at.desc()).limit(200)
    if allowed is not None:
        stmt = stmt.where(SensorInstallVisit.farm_id.in_(allowed or [-1]))
    if status is not None:
        stmt = stmt.where(SensorInstallVisit.status == status)
    visits = db.execute(stmt).scalars().all()
    return [_serialize(v) for v in visits]


def _apply_update(visit: SensorInstallVisit, payload: InstallVisitUpdateIn) -> list[str]:
    """Validate + apply a partial update. Returns fields that changed."""
    changes: dict = payload.model_dump(exclude_unset=True)

    target_status = changes.get("status")
    if visit.status == VisitStatus.completed:
        raise HTTPException(409, "Completed visits cannot be modified")

    if target_status == VisitStatus.cancelled:
        if visit.status not in _OPEN_STATUSES:
            raise HTTPException(409, "Only requested/scheduled visits can be cancelled")
        visit.status = VisitStatus.cancelled
        visit.cancel_reason = changes.get("cancel_reason") or "No reason given"
        return ["status"]

    unknown = set(changes) - {"status", "scheduled_at", "official_name", "official_phone"}
    if unknown:
        raise HTTPException(422, f"Unsupported fields: {sorted(unknown)}")

    merged = {
        "scheduled_at": visit.scheduled_at,
        "official_name": visit.official_name,
        "official_phone": visit.official_phone,
        **{k: v for k, v in changes.items() if k != "status"},
    }
    missing = [k for k in ("scheduled_at", "official_name", "official_phone") if not merged[k]]
    if missing:
        raise HTTPException(422, f"Scheduling requires {', '.join(missing)}")

    if target_status == VisitStatus.scheduled or (
        target_status is None and any(k in changes for k in ("scheduled_at", "official_name", "official_phone"))
    ):
        if visit.status == VisitStatus.cancelled:
            raise HTTPException(409, "Cancelled visits cannot be scheduled")
        was_scheduled = visit.status == VisitStatus.scheduled
        visit.scheduled_at = merged["scheduled_at"]
        visit.official_name = merged["official_name"]
        visit.official_phone = merged["official_phone"]
        visit.status = VisitStatus.scheduled
        return ["rescheduled"] if was_scheduled else ["scheduled"]

    if target_status == VisitStatus.completed:
        if visit.status != VisitStatus.scheduled:
            raise HTTPException(422, "Only scheduled visits can be completed")
        visit.status = VisitStatus.completed
        visit.completed_at = utcnow()
        return ["status"]

    raise HTTPException(422, "Nothing to update")


@router.patch("/{visit_id}")
def update_visit(
    visit_id: int,
    payload: InstallVisitUpdateIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.admin)),
):
    visit = db.get(SensorInstallVisit, visit_id)
    if not visit:
        raise HTTPException(404, "Visit not found")
    applied = _apply_update(visit, payload)

    if "scheduled" in applied or "rescheduled" in applied:
        alert_service.create_alert(
            db,
            farm_id=visit.farm_id,
            type_=AlertType.INSTALL_UPDATE,
            severity=AlertSeverity.info,
            title="Sensor installation scheduled",
            message=(
                f"{visit.official_name} ({visit.official_phone}) will install IoT sensors "
                f"at {ist_str(ensure_aware(visit.scheduled_at))}. "
                f"Requested slot: {visit.preferred_slot.value}, {visit.preferred_date.strftime('%d %b %Y')}."
            ),
            related_type="install_visit",
            related_id=visit.id,
            audience=AlertAudience.farmer,
        )
    db.commit()
    db.refresh(visit)
    out = _serialize(visit)
    out["applied"] = applied
    return out


@router.post("/{visit_id}/cancel")
def cancel_visit(
    visit_id: int,
    reason: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(any_authenticated),
):
    visit = db.get(SensorInstallVisit, visit_id)
    if not visit:
        raise HTTPException(404, "Visit not found")
    ensure_farm_access(user, visit.farm_id)
    if user.role != Role.admin and visit.requested_by_user_id not in (None, user.id):
        raise HTTPException(403, "Not your request")
    if visit.status not in _OPEN_STATUSES:
        raise HTTPException(409, "Only requested/scheduled visits can be cancelled")
    visit.status = VisitStatus.cancelled
    visit.cancel_reason = reason or "Cancelled by " + ("admin" if user.role == Role.admin else "farmer")
    db.commit()
    db.refresh(visit)
    return _serialize(visit)
