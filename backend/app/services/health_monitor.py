"""Animal health monitoring: anomaly detection + dual notification (owner & vet).

Called after the IoT simulator advances. Detection is deterministic and lazy --
no worker needed. Every anomaly alert explicitly names the notified parties
(farm owner + veterinary team) and gives stewardship-safe guidance.
"""

from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Alert, Animal, SensorReading, User
from app.models.enums import AlertSeverity, AlertType, Role
from app.services import alert_service
from app.utils.timeutil import ensure_aware, ist_str, utcnow

FEVER_C = 39.5
CRITICAL_FEVER_C = 40.5
BUCKET_HOURS = 0.25  # sensor cadence: 15 minutes


@dataclass
class HealthAssessment:
    status: str  # normal | watch | fever
    current_temp_c: float
    avg_temp_c: float
    peak_temp_c: float
    fever_hours: float
    activity_drop_pct: float
    rumination_delta_pct: float
    readings_count: int


def assess(db: Session, animal: Animal, hours: int = 24) -> HealthAssessment | None:
    cutoff = ensure_aware(utcnow()) - timedelta(hours=hours)
    readings = db.execute(
        select(SensorReading)
        .where(SensorReading.animal_id == animal.id, SensorReading.recorded_at > cutoff)
        .order_by(SensorReading.recorded_at.asc())
    ).scalars().all()
    if not readings:
        return None

    temps = [r.body_temp_c for r in readings]
    acts = [r.activity_index for r in readings]
    rums = [r.rumination_min for r in readings if r.rumination_min is not None]

    current = temps[-1]
    avg_t = sum(temps) / len(temps)
    peak_t = max(temps)
    fever_hours = sum(1 for t in temps if t >= FEVER_C) * BUCKET_HOURS

    # activity drop: first third (baseline) vs last quarter (now)
    baseline_n = max(1, len(acts) // 3)
    baseline = sum(acts[:baseline_n]) / baseline_n
    recent = sum(acts[-max(1, len(acts) // 4):]) / max(1, len(acts) // 4)
    activity_drop = max(0.0, (baseline - recent) / baseline * 100) if baseline else 0.0

    rum_delta = 0.0
    if len(rums) >= 8:
        r_base = sum(rums[: len(rums) // 3]) / max(1, len(rums) // 3)
        r_now = sum(rums[-max(1, len(rums) // 4):]) / max(1, len(rums) // 4)
        rum_delta = max(0.0, (r_base - r_now) / r_base * 100) if r_base else 0.0

    if current >= FEVER_C or fever_hours >= 3:
        status = "fever"
    elif peak_t >= FEVER_C or activity_drop >= 30:
        status = "watch"
    else:
        status = "normal"

    return HealthAssessment(
        status=status,
        current_temp_c=round(current, 2),
        avg_temp_c=round(avg_t, 2),
        peak_temp_c=round(peak_t, 2),
        fever_hours=round(fever_hours, 2),
        activity_drop_pct=round(activity_drop, 1),
        rumination_delta_pct=round(rum_delta, 1),
        readings_count=len(readings),
    )


def _notify_parties(db: Session, animal: Animal) -> tuple[str | None, list[User]]:
    owner = db.execute(
        select(User).where(User.farm_id == animal.farm_id, User.role == Role.farmer)
    ).scalars().first()
    vets = list(db.execute(select(User).where(User.role == Role.vet)).scalars().all())
    return (owner.full_name if owner else None), vets


def run_detection(db: Session, animal: Animal) -> list[Alert]:
    """Scan the last 24h of sensor data; raise/refresh anomaly alerts.

    Alerts are addressed to BOTH the owner and the veterinary team (names are
    embedded in the message; visibility is role-scoped in the API layer).
    """
    owner_name, vets = _notify_parties(db, animal)
    vet_names = ", ".join("Dr. " + v.full_name for v in vets) or " veterinary on-call"
    notified = f"Owner ({owner_name or 'farm'}) and veterinary team ({vet_names}) notified."
    guidance = (
        "Do NOT start antimicrobials without veterinary examination; if prescribed, "
        "record the course so withdrawal clocks and MRL safeguards activate."
    )

    assessment = assess(db, animal, hours=24)
    created: list[Alert] = []
    if assessment is None or assessment.status == "normal":
        return created

    existing = db.execute(
        select(Alert).where(
            Alert.type == AlertType.SENSOR_ANOMALY,
            Alert.animal_id == animal.id,
            Alert.resolved_at.is_(None),
        )
    ).scalars().first()

    if existing is None:
        critical = assessment.current_temp_c >= CRITICAL_FEVER_C or assessment.fever_hours >= 6
        alert = alert_service.create_alert(
            db,
            farm_id=animal.farm_id,
            animal_id=animal.id,
            type_=AlertType.SENSOR_ANOMALY,
            severity=AlertSeverity.critical if critical else AlertSeverity.warning,
            title=(
                f"🌡️ {animal.tag_id}: fever {assessment.current_temp_c}°C "
                f"({assessment.fever_hours:.1f}h sustained)"
            ),
            message=(
                f"IoT collar: current {assessment.current_temp_c}°C (24h peak "
                f"{assessment.peak_temp_c}°C), activity down {assessment.activity_drop_pct}%, "
                f"rumination down {assessment.rumination_delta_pct}%. {notified} {guidance}"
            ),
            related_type="sensor_episode",
            related_id=animal.id,
        )
        created.append(alert)

    # ML outbreak escalation
    from app.services.ml import features as feat
    from app.services.ml import serve

    feats = feat.outbreak_features(db, animal)
    pred = serve.predict_outbreak(feats) if feats else None
    if pred and pred["risk"] >= 0.66:
        existing_outbreak = db.execute(
            select(Alert).where(
                Alert.type == AlertType.OUTBREAK_RISK,
                Alert.animal_id == animal.id,
                Alert.resolved_at.is_(None),
            )
        ).scalars().first()
        if existing_outbreak is None:
            alert = alert_service.create_alert(
                db,
                farm_id=animal.farm_id,
                animal_id=animal.id,
                type_=AlertType.OUTBREAK_RISK,
                severity=AlertSeverity.critical,
                title=f"🤖 ML OUTBREAK RISK HIGH for {animal.tag_id} ({pred['risk']:.0%})",
                message=(
                    f"Predictive model flags disease-outbreak risk {pred['risk']:.0%} "
                    f"(top factor: {pred['top_factors'][0]['factor']}). {notified} "
                    f"Isolate if clinical signs appear; monitor herd contacts. "
                    f"Synthetic-data demo model."
                ),
                related_type="ml_prediction",
                related_id=animal.id,
            )
            created.append(alert)

    return created


def open_health_alerts(db: Session, animal: Animal) -> list[Alert]:
    return list(
        db.execute(
            select(Alert)
            .where(
                Alert.animal_id == animal.id,
                Alert.resolved_at.is_(None),
                Alert.type.in_([AlertType.SENSOR_ANOMALY, AlertType.OUTBREAK_RISK]),
            )
            .order_by(Alert.created_at.desc())
        ).scalars().all()
    )
