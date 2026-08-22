"""Analytics aggregations for dashboards and reports. All queries are scoped
by farm ids (None = all farms)."""

from datetime import timedelta

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models import (
    Administration,
    Alert,
    Animal,
    Drug,
    ResidueTest,
    SaleEvent,
)
from app.models.enums import SaleProduct
from app.models.enums import AWaReClass
from app.utils.timeutil import ensure_aware, utcnow


def dashboard_stats(db: Session, farm_ids: list[int] | None) -> dict:
    now = ensure_aware(utcnow())
    animal_f = Animal.farm_id.in_(farm_ids) if farm_ids is not None else None

    q_animals = select(func.count()).select_from(Animal).where(Animal.status == "active")
    if animal_f is not None:
        q_animals = q_animals.where(animal_f)
    total_animals = db.execute(q_animals).scalar() or 0

    # treatments in last 30 days
    cutoff = now - timedelta(days=30)
    q_amu = (
        select(func.count())
        .select_from(Administration)
        .join(Animal, Administration.animal_id == Animal.id)
        .where(Administration.started_at > cutoff)
    )
    if animal_f is not None:
        q_amu = q_amu.where(animal_f)
    amu_30d = db.execute(q_amu).scalar() or 0

    # supervised share
    q_sup = q_amu.where(Administration.prescription_id.isnot(None))
    supervised_30d = db.execute(q_sup).scalar() or 0

    # open violations
    q_viol = select(func.count()).select_from(SaleEvent).where(SaleEvent.is_violation.is_(True))
    if farm_ids is not None:
        q_viol = q_viol.where(SaleEvent.farm_id.in_(farm_ids))
    violations = db.execute(q_viol).scalar() or 0

    q_alerts = select(func.count()).select_from(Alert).where(
        Alert.resolved_at.is_(None), Alert.severity == "critical"
    )
    if farm_ids is not None:
        q_alerts = q_alerts.where(Alert.farm_id.in_(farm_ids))
    critical_alerts = db.execute(q_alerts).scalar() or 0

    return {
        "total_animals": total_animals,
        "amu_30d": amu_30d,
        "supervised_share": round(supervised_30d / amu_30d, 3) if amu_30d else None,
        "violations_total": violations,
        "critical_alerts_open": critical_alerts,
    }


def aware_breakdown(db: Session, farm_ids: list[int] | None, months: int = 6) -> list[dict]:
    """WHO AWaRe classification share of administrations."""
    since = ensure_aware(utcnow()) - timedelta(days=30 * months)
    stmt = (
        select(Drug.aware_class, func.count())
        .join(Administration, Administration.drug_id == Drug.id)
        .where(Administration.started_at > since)
        .group_by(Drug.aware_class)
    )
    if farm_ids is not None:
        stmt = stmt.join(Animal, Administration.animal_id == Animal.id).where(
            Animal.farm_id.in_(farm_ids)
        )
    rows = db.execute(stmt).all()
    total = sum(c for _, c in rows) or 1
    return [
        {
            "aware_class": cls.value if hasattr(cls, "value") else str(cls),
            "count": c,
            "share": round(c / total, 3),
        }
        for cls, c in sorted(rows, key=lambda r: -r[1])
    ]


def drug_leaderboard(db: Session, farm_ids: list[int] | None, limit: int = 10) -> list[dict]:
    stmt = (
        select(
            Drug.generic_name,
            Drug.drug_class,
            Drug.aware_class,
            func.count().label("uses"),
        )
        .join(Administration, Administration.drug_id == Drug.id)
        .group_by(Drug.id)
        .order_by(func.count().desc())
        .limit(limit)
    )
    if farm_ids is not None:
        stmt = stmt.join(Animal, Administration.animal_id == Animal.id).where(
            Animal.farm_id.in_(farm_ids)
        )
    return [
        {
            "drug_name": name,
            "drug_class": drug_class,
            "aware_class": cls.value if hasattr(cls, "value") else str(cls),
            "uses": uses,
        }
        for name, drug_class, cls, uses in db.execute(stmt).all()
    ]


def monthly_trend(db: Session, farm_ids: list[int] | None, months: int = 6) -> list[dict]:
    """Administrations per month + violation count per month."""
    since = ensure_aware(utcnow()) - timedelta(days=30 * months)
    base = (
        select(Administration, Animal)
        .join(Animal, Administration.animal_id == Animal.id)
        .where(Administration.started_at > since)
    )
    if farm_ids is not None:
        base = base.where(Animal.farm_id.in_(farm_ids))
    buckets: dict[str, int] = {}
    for adm, _ in db.execute(base).all():
        key = ensure_aware(adm.started_at).strftime("%Y-%m")
        buckets[key] = buckets.get(key, 0) + 1
    vs = select(SaleEvent).where(
        SaleEvent.is_violation.is_(True), SaleEvent.occurred_at > since
    )
    if farm_ids is not None:
        vs = vs.where(SaleEvent.farm_id.in_(farm_ids))
    vbuckets: dict[str, int] = {}
    for s in db.execute(vs).scalars().all():
        key = ensure_aware(s.occurred_at).strftime("%Y-%m")
        vbuckets[key] = vbuckets.get(key, 0) + 1

    out = []
    for month in sorted(buckets.keys() | vbuckets.keys()):
        out.append({"month": month, "treatments": buckets.get(month, 0), "violations": vbuckets.get(month, 0)})
    return out


def sales_analytics(db: Session, farm_ids: list[int] | None, months: int = 6) -> dict:
    """Animal-product sales: volumes by month/product, revenue, and the
    clean-vs-violating split of recorded sales."""
    since = ensure_aware(utcnow()) - timedelta(days=30 * months)
    stmt = select(SaleEvent).where(SaleEvent.occurred_at > since)
    if farm_ids is not None:
        stmt = stmt.where(SaleEvent.farm_id.in_(farm_ids))
    sales = db.execute(stmt).scalars().all()

    monthly: dict[str, dict[str, float]] = {}
    clean, violating = 0, 0
    product_totals: dict[str, float] = {}
    revenue_total = 0.0

    for s in sales:
        month = ensure_aware(s.occurred_at).strftime("%Y-%m") if s.occurred_at else "?"
        bucket = monthly.setdefault(
            month, {"milk_litres": 0, "eggs_trays": 0, "meat_kg": 0, "revenue_inr": 0}
        )
        key = {
            SaleProduct.milk: "milk_litres",
            SaleProduct.eggs: "eggs_trays",
            SaleProduct.meat: "meat_kg",
            SaleProduct.live_animal: "meat_kg",
        }.get(s.product_type)
        if key:
            bucket[key] += s.quantity
            product_totals[s.product_type.value] = (
                product_totals.get(s.product_type.value, 0) + s.quantity
            )
        if s.amount_inr:
            bucket["revenue_inr"] += s.amount_inr
            revenue_total += s.amount_inr
        if s.is_violation:
            violating += 1
        else:
            clean += 1

    return {
        "monthly": [
            {"month": m, **vals} for m, vals in sorted(monthly.items())
        ],
        "compliance": {"clean_sales": clean, "violating_sales": violating},
        "product_totals": [
            {"product": p, "quantity": round(q, 1)} for p, q in product_totals.items()
        ],
        "revenue_total_inr": round(revenue_total, 0),
    }


def monthly_report(db: Session, farm_ids: list[int] | None) -> dict:
    stats = dashboard_stats(db, farm_ids)
    return {
        **stats,
        "aware_breakdown": aware_breakdown(db, farm_ids, months=1),
        "drug_leaderboard": drug_leaderboard(db, farm_ids),
        "monthly_trend": monthly_trend(db, farm_ids, months=6),
        "generated_for_farms": farm_ids if farm_ids is not None else "ALL",
    }
