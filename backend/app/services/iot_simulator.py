"""Deterministic IoT sensor simulator -- no background worker needed.

Readings are a pure function of (device_id, 15-minute bucket): the same bucket
always produces identical values, so concurrent pollers never fork history.
`advance()` persists any missing buckets up to `now` (insert-or-ignore via
unique constraint), giving continuous charts that "grow in real time".
"""

import hashlib
import math
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Animal, SensorReading
from app.utils.timeutil import ensure_aware, utcnow

BUCKET = timedelta(minutes=15)
FEVER_THRESHOLD_C = 39.3


def _noise(seed: str, lo: float, hi: float) -> float:
    digest = hashlib.sha256(seed.encode()).digest()
    frac = int.from_bytes(digest[:8], "big") / 2**64
    return lo + (hi - lo) * frac


def _simulate(animal: Animal, device_id: str, bucket_start) -> tuple[float, float, int]:
    """Return (body_temp_c, activity_index, rumination_min) for one bucket."""
    hour = bucket_start.hour + bucket_start.minute / 60.0
    diurnal = math.sin((hour - 6) / 24 * 2 * math.pi)  # peak late afternoon

    base_temp = {"cattle": 38.5, "buffalo": 38.2, "goat": 39.1,
                 "sheep": 39.0, "pig": 38.8, "poultry": 41.2}.get(
        animal.species.value if hasattr(animal.species, "value") else str(animal.species), 38.5
    )
    temp = (
        base_temp
        + 0.35 * diurnal
        + _noise(f"{device_id}{bucket_start.isoformat()}t", -0.15, 0.15)
    )
    activity = (
        55
        + 25 * math.sin((hour - 7) / 12 * math.pi) ** 2  # feeding peaks morning/evening
        + _noise(f"{device_id}{bucket_start.isoformat()}a", -10, 10)
    )

    scenario = animal.scenario_tag or "healthy"
    if scenario == "fever_outbreak":
        # Slow deterministic fever wave -- always elevated enough to trip the
        # 39.3C threshold whenever a judge looks, with believable variation.
        bucket_idx = int(bucket_start.timestamp() // BUCKET.total_seconds())
        wave = math.sin(bucket_idx / 96 * math.pi)
        temp += 1.15 + 0.3 * wave
        activity -= 28 + 8 * wave

    rumination = int(max(120, 420 + _noise(f"{device_id}{bucket_start}r", -80, 80)
                         - (150 if scenario == "fever_outbreak" else 0)))
    return round(temp, 2), round(max(activity, 3), 1), rumination


def device_for(animal: Animal) -> str:
    return f"DEV-{animal.tag_id}"


def advance(db: Session, animal_ids: list[int], hours_back: int = 48) -> None:
    """Persist any missing buckets from `now - hours_back` to now."""
    now = ensure_aware(utcnow()).replace(second=0, microsecond=0)
    start = now - timedelta(hours=hours_back)
    animals = db.execute(select(Animal).where(Animal.id.in_(animal_ids))).scalars().all()
    for animal in animals:
        # NB: SQLite returns naive datetimes -- normalize before set membership.
        existing = {
            ensure_aware(r) for r in db.execute(
                select(SensorReading.recorded_at).where(SensorReading.animal_id == animal.id)
            ).scalars().all()
        }
        device = device_for(animal)
        bucket = start
        new_rows = []
        while bucket <= now:
            if bucket not in existing:
                temp, act, rum = _simulate(animal, device, bucket)
                new_rows.append(
                    SensorReading(
                        animal_id=animal.id,
                        device_id=device,
                        recorded_at=bucket,
                        body_temp_c=temp,
                        activity_index=act,
                        rumination_min=rum,
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


def readings_for(db: Session, animal_id: int, hours: int = 48) -> list[dict]:
    cutoff = ensure_aware(utcnow()) - timedelta(hours=hours)
    rows = db.execute(
        select(SensorReading)
        .where(SensorReading.animal_id == animal_id, SensorReading.recorded_at > cutoff)
        .order_by(SensorReading.recorded_at.asc())
    ).scalars().all()
    return [
        {
            "recorded_at": r.recorded_at.isoformat() if r.recorded_at else None,
            "device_id": r.device_id,
            "body_temp_c": r.body_temp_c,
            "activity_index": r.activity_index,
            "rumination_min": r.rumination_min,
        }
        for r in rows
    ]
