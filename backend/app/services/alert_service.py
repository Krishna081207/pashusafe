"""Alert creation with dedupe + lazy refresh (no background scheduler needed).

R5 (upcoming clearance) and sensor anomalies are evaluated on-demand whenever
alerts or dashboards are fetched, so the demo never depends on a worker.
"""

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Alert, Animal, Administration, SensorReading, WithdrawalPeriod
from app.models.enums import AlertSeverity, AlertType
from app.utils.timeutil import ensure_aware, ist_str, utcnow


def create_alert(
    db: Session,
    *,
    farm_id: int,
    type_: AlertType,
    severity: AlertSeverity,
    title: str,
    message: str,
    animal_id: int | None = None,
    related_type: str | None = None,
    related_id: int | None = None,
    dedupe_window: timedelta | None = None,
) -> Alert:
    if dedupe_window is not None:
        cutoff = utcnow() - dedupe_window
        exists = db.execute(
            select(Alert).where(
                Alert.farm_id == farm_id,
                Alert.type == type_,
                Alert.related_id == related_id,
                Alert.created_at > cutoff,
            )
        ).scalar_one_or_none()
        if exists:
            return exists

    alert = Alert(
        farm_id=farm_id,
        animal_id=animal_id,
        type=type_,
        severity=severity,
        title=title,
        message=message,
        related_type=related_type,
        related_id=related_id,
    )
    db.add(alert)
    db.flush()
    return alert


def refresh_lazy_alerts(db: Session, farm_ids: list[int] | None) -> None:
    """Evaluate R5 + sensor anomalies for the given farms (None = all farms)."""
    now = ensure_aware(utcnow())

    # --- R5: clearance within next 24h -------------------------------------
    stmt = (
        select(WithdrawalPeriod, Administration, Animal)
        .join(Administration, WithdrawalPeriod.administration_id == Administration.id)
        .join(Animal, Administration.animal_id == Animal.id)
        .where(
            WithdrawalPeriod.status == "active",
            WithdrawalPeriod.clears_at > now,
            WithdrawalPeriod.clears_at <= now + timedelta(hours=24),
        )
    )
    if farm_ids is not None:
        stmt = stmt.where(Animal.farm_id.in_(farm_ids))
    for wp, adm, animal in db.execute(stmt).all():
        existing = db.execute(
            select(Alert).where(
                Alert.type == AlertType.UPCOMING_CLEARANCE,
                Alert.related_type == "withdrawal_period",
                Alert.related_id == wp.id,
            )
        ).scalar_one_or_none()
        if existing:
            continue
        create_alert(
            db,
            farm_id=animal.farm_id,
            animal_id=animal.id,
            type_=AlertType.UPCOMING_CLEARANCE,
            severity=AlertSeverity.info,
            title=f"{animal.tag_id}: {wp.tissue.value} withdrawal ends soon",
            message=(
                f"{animal.tag_id} becomes {wp.tissue.value}-clear at "
                f"{ist_str(wp.clears_at)} (administration #{wp.administration_id})."
            ),
            related_type="withdrawal_period",
            related_id=wp.id,
        )

    # --- sensor anomalies are handled by services/health_monitor.py --------
    # (raised on IoT status fetch with owner+vet notification names) ---------


def serialize(alert: Alert) -> dict:
    return {
        "id": alert.id,
        "farm_id": alert.farm_id,
        "animal_id": alert.animal_id,
        "type": alert.type.value,
        "severity": alert.severity.value,
        "title": alert.title,
        "message": alert.message,
        "related_type": alert.related_type,
        "related_id": alert.related_id,
        "is_read": alert.is_read,
        "resolved": alert.resolved_at is not None,
        "created_at": ensure_aware(alert.created_at).isoformat() if alert.created_at else None,
    }
