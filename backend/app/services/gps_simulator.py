"""Deterministic GPS simulator -- the location twin of iot_simulator.

Positions are a pure function of (animal_id, 5-minute bucket): concurrent
pollers never fork history, and `advance_positions()` persists missing buckets
insert-or-ignore so the map "grows in real time" with no worker process.

Animals wander inside a FIXED home range around their farm's geofence centre,
deliberately independent of the configured fence radius -- so shrinking the
boundary in the UI immediately puts animals outside it (the live demo control).
An animal tagged `scenario_tag="geofence_breach"` additionally steps beyond
whatever fence is configured for a 30-minute window every 2 hours, then
returns -- giving the demo both an open breach and a resolved one.

Breach evaluation always recomputes distance from the stored coordinates
against the CURRENT fence, so editing the circle takes effect on the next poll.
"""

import hashlib
import math
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Alert, Animal, AnimalPosition, Geofence
from app.models.enums import AlertAudience, AlertSeverity, AlertType
from app.services import alert_service
from app.services.geo import haversine_m, offset_latlng
from app.utils.timeutil import ensure_aware, ist_str, utcnow

BUCKET = timedelta(minutes=5)
BUCKET_S = int(BUCKET.total_seconds())
CYCLE_S = 7200                  # breach story repeats every 2 h
OUT_FROM, OUT_TO = 3600, 5400   # ...for the 30 min in the middle of each cycle
HOME_RANGE_M = 220.0            # normal wandering envelope, fence-independent


def _hash01(seed: str) -> float:
    digest = hashlib.sha256(seed.encode()).digest()
    return int.from_bytes(digest[:8], "big") / 2**64


def device_for(animal: Animal) -> str:
    return f"GPS-{animal.tag_id}"


def position_for(animal: Animal, fence: Geofence, bucket_start):
    """Return (lat, lng, distance_from_center_m, inside_geofence) for one bucket."""
    ts = int(bucket_start.timestamp())
    angle = _hash01(f"ang{animal.id}{ts // BUCKET_S}") * 2 * math.pi
    # slow radial drift, re-drawn once per hour
    dist = HOME_RANGE_M * (0.15 + 0.55 * _hash01(f"rad{animal.id}{ts // 3600}"))

    if fence.enabled and (animal.scenario_tag or "") == "geofence_breach" \
            and OUT_FROM <= ts % CYCLE_S < OUT_TO:
        dist = fence.radius_m * (1.35 + 0.35 * _hash01(f"out{animal.id}{ts // BUCKET_S}"))

    north = dist * math.cos(angle)
    east = dist * math.sin(angle)
    lat, lng = offset_latlng(fence.center_lat, fence.center_lng, north, east)
    actual = haversine_m(lat, lng, fence.center_lat, fence.center_lng)
    return lat, lng, actual, actual <= fence.radius_m


def is_outside(pos: AnimalPosition | tuple, fence: Geofence) -> bool:
    """Breach test against the CURRENT fence (stored flags may be stale)."""
    if isinstance(pos, AnimalPosition):
        lat, lng = pos.lat, pos.lng
    else:
        lat, lng = pos
    if not fence.enabled:
        return False
    return haversine_m(lat, lng, fence.center_lat, fence.center_lng) > fence.radius_m


def advance_positions(
    db: Session,
    animals: list[Animal],
    fences: dict[int, Geofence] | None = None,
    hours_back: int = 6,
) -> None:
    """Persist any missing buckets from `now - hours_back` to now."""
    now = ensure_aware(utcnow()).replace(second=0, microsecond=0)
    start = now - timedelta(hours=hours_back)
    if fences is None:
        farm_ids = {a.farm_id for a in animals}
        rows = db.execute(select(Geofence).where(Geofence.farm_id.in_(farm_ids or [-1]))).scalars().all()
        fences = {g.farm_id: g for g in rows}

    for animal in animals:
        fence = fences.get(animal.farm_id)
        if fence is None:  # cannot simulate without a farm centre
            continue
        existing = {
            ensure_aware(r) for r in db.execute(
                select(AnimalPosition.recorded_at).where(AnimalPosition.animal_id == animal.id)
            ).scalars().all()
        }
        device = device_for(animal)
        new_rows: list[AnimalPosition] = []
        bucket = start
        while bucket <= now:
            if bucket not in existing:
                lat, lng, actual, _inside = position_for(animal, fence, bucket_start=bucket)
                plat, plng, _, _ = position_for(animal, fence, bucket_start=bucket - BUCKET)
                hop_m = haversine_m(plat, plng, lat, lng)
                speed = round(hop_m * 3.6 / BUCKET_S, 1)  # m over 5 min -> km/h
                new_rows.append(
                    AnimalPosition(
                        animal_id=animal.id,
                        device_id=device,
                        recorded_at=bucket,
                        lat=lat,
                        lng=lng,
                        speed_kmh=speed,
                        distance_from_center_m=actual,
                        inside_geofence=actual <= fence.radius_m,
                    )
                )
            bucket += BUCKET
            if len(new_rows) >= 400:  # chunk inserts
                db.add_all(new_rows)
                db.flush()
                new_rows = []
        if new_rows:
            db.add_all(new_rows)
    db.commit()


def sync_breach_alerts(db: Session, animal: Animal, fence: Geofence) -> Alert | None:
    """Raise/resolve the farmer-only GEOFENCE_BREACH alert from latest position."""
    latest = db.execute(
        select(AnimalPosition)
        .where(AnimalPosition.animal_id == animal.id)
        .order_by(AnimalPosition.recorded_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if latest is None:
        return None

    open_alert = db.execute(
        select(Alert).where(
            Alert.type == AlertType.GEOFENCE_BREACH,
            Alert.related_type == "geofence",
            Alert.related_id == animal.id,
            Alert.resolved_at.is_(None),
        )
    ).scalar_one_or_none()

    outside = is_outside(latest, fence)

    if outside and open_alert is None:
        beyond = round((latest.distance_from_center_m or 0) - fence.radius_m)
        return alert_service.create_alert(
            db,
            farm_id=animal.farm_id,
            animal_id=animal.id,
            type_=AlertType.GEOFENCE_BREACH,
            severity=AlertSeverity.warning,
            title=f"{animal.tag_id} left the geofence",
            message=(
                f"{animal.tag_id} is {max(beyond, 0)} m beyond your farm boundary "
                f"(last seen {ist_str(ensure_aware(latest.recorded_at))}). "
                f"Only you are notified -- vets and regulators cannot see this."
            ),
            related_type="geofence",
            related_id=animal.id,
            audience=AlertAudience.farmer,
        )

    if not outside and open_alert is not None:
        open_alert.resolved_at = utcnow()
        open_alert.message += (
            f" {animal.tag_id} returned inside the boundary "
            f"({ist_str(ensure_aware(latest.recorded_at))})."
        )
        return open_alert
    return None
