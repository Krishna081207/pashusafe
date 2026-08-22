"""Feature builders shared by training and serving. All SQL aggregates scoped
to a single animal."""

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Administration, Animal, Drug, SaleEvent, SensorReading
from app.utils.timeutil import ensure_aware, utcnow

MRL_FEATURES = [
    "amu_30d", "amu_90d", "distinct_drugs_90d", "watch_reserve_share",
    "days_until_clear", "past_violations", "mean_course_days",
    "unsupervised_share", "herd_size",
]

SPECIES_INDEX = {"cattle": 0, "buffalo": 1, "goat": 2, "sheep": 3, "pig": 4, "poultry": 5}


def mrl_features(db: Session, animal: Animal) -> dict:
    now = ensure_aware(utcnow())
    c30 = now - timedelta(days=30)
    c90 = now - timedelta(days=90)

    def count(since):
        return (
            db.execute(
                select(func.count())
                .select_from(Administration)
                .where(Administration.animal_id == animal.id, Administration.started_at > since)
            ).scalar() or 0
        )

    amu_30d = count(c30)
    amu_90d = count(c90)

    rows = db.execute(
        select(Administration.course_days, Administration.prescription_id, Drug.aware_class)
        .select_from(Administration)
        .join(Drug, Administration.drug_id == Drug.id)
        .where(Administration.animal_id == animal.id, Administration.started_at > c90)
    ).all()

    distinct = db.execute(
        select(func.count(func.distinct(Administration.drug_id)))
        .select_from(Administration)
        .where(Administration.animal_id == animal.id, Administration.started_at > c90)
    ).scalar() or 0

    watch_reserve = sum(
        1 for _, _, aware in rows if (aware.value if hasattr(aware, "value") else str(aware))
        in ("Watch", "Reserve")
    )
    supervised = sum(1 for _, rx, _ in rows if rx is not None)

    herd_size = db.execute(
        select(func.count())
        .select_from(Animal)
        .where(Animal.farm_id == animal.farm_id, Animal.status == "active")
    ).scalar() or 0

    past_violations = db.execute(
        select(func.count())
        .select_from(SaleEvent)
        .where(SaleEvent.animal_id == animal.id, SaleEvent.is_violation.is_(True))
    ).scalar() or 0

    # days until every tissue clears (0 when already compliant)
    from app.services.mrl_engine import load_open_windows, summarize_windows

    status = summarize_windows(load_open_windows(db, [animal.id], now), now)
    if status.next_clearance is not None:
        days_until_clear = max((status.next_clearance - now).total_seconds() / 86400, 0)
    else:
        days_until_clear = 0

    return {
        "amu_30d": float(amu_30d),
        "amu_90d": float(amu_90d),
        "distinct_drugs_90d": float(distinct),
        "watch_reserve_share": round(watch_reserve / len(rows), 3) if rows else 0.0,
        "days_until_clear": round(days_until_clear, 2),
        "past_violations": float(past_violations),
        "mean_course_days": round(sum(cd for cd, _, _ in rows) / len(rows), 2) if rows else 0.0,
        "unsupervised_share": round(1 - supervised / len(rows), 3) if rows else 0.0,
        "herd_size": float(herd_size),
        "species_idx": SPECIES_INDEX.get(
            animal.species.value if hasattr(animal.species, "value") else str(animal.species), 0
        ),
    }


OUTBREAK_FEATURES = ["temp_zscore", "activity_drop_pct", "amu_30d", "farm_amu_spike"]


def outbreak_features(db: Session, animal: Animal) -> dict | None:
    now = ensure_aware(utcnow())

    def since(days):
        return now - timedelta(days=days)

    readings = db.execute(
        select(SensorReading.body_temp_c, SensorReading.activity_index)
        .where(SensorReading.animal_id == animal.id, SensorReading.recorded_at > since(7))
        .order_by(SensorReading.recorded_at.asc())
    ).all()
    if not readings:
        return None

    temps = [t for t, _ in readings]
    acts = [a for _, a in readings]
    recent_t, recent_a = temps[-1], acts[-1]

    hist_temps = temps[:-1] or [recent_t]
    hist_acts = acts[:-1] or [recent_a]

    import statistics

    mean_t = statistics.fmean(hist_temps)
    std_t = statistics.pstdev(hist_temps) or 0.5
    mean_a = statistics.fmean(hist_acts) or 1.0

    temp_zscore = round((recent_t - mean_t) / std_t, 2)
    activity_drop_pct = round(max(0.0, (mean_a - recent_a) / mean_a * 100), 1)

    amu_30d = db.execute(
        select(func.count())
        .select_from(Administration)
        .where(Administration.animal_id == animal.id, Administration.started_at > since(30))
    ).scalar() or 0

    farm_peers = db.execute(
        select(Animal.id).where(Animal.farm_id == animal.farm_id)
    ).scalars().all()
    farm_amu_spike = 0
    if farm_peers:
        week_now = db.execute(
            select(func.count())
            .select_from(Administration)
            .where(
                Administration.animal_id.in_(list(farm_peers)),
                Administration.started_at > now - timedelta(days=7),
            )
        ).scalar() or 0
        week_prev = db.execute(
            select(func.count())
            .select_from(Administration)
            .where(
                Administration.animal_id.in_(list(farm_peers)),
                Administration.started_at > now - timedelta(days=14),
                Administration.started_at <= now - timedelta(days=7),
            )
        ).scalar() or 0
        farm_amu_spike = week_now - week_prev

    return {
        "temp_zscore": temp_zscore,
        "activity_drop_pct": activity_drop_pct,
        "amu_30d": float(amu_30d),
        "farm_amu_spike": float(farm_amu_spike),
    }


def vectorize(feature_names: list[str], feats: dict, extra_names: list[str] | None = None):
    keys = feature_names + (extra_names or [])
    return [float(feats.get(k, 0.0)) for k in keys]
