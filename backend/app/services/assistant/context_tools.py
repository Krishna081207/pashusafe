"""Farm-data tools shared by BOTH assistant modes (Claude tool-use loop and
offline intent fallback). Each returns a compact dict ready to be rendered."""

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Administration, Alert, Animal, Drug, SaleEvent
from app.services import analytics_service
from app.services.mrl_engine import farm_compliance
from app.utils.timeutil import ensure_aware, ist_str, utcnow


def compliance_summary(db: Session, farm_ids: list[int] | None) -> dict:
    stmt = select(Animal).where(Animal.status == "active")
    if farm_ids is not None:
        stmt = stmt.where(Animal.farm_id.in_(farm_ids or [-1]))
    animals = db.execute(stmt).scalars().all()
    by_farm: dict[int, int] = {}
    for a in animals:
        by_farm[a.farm_id] = by_farm.get(a.farm_id, 0) + 1

    out = {"total_active_animals": len(animals), "farms": len(by_farm)}
    stats = analytics_service.dashboard_stats(db, farm_ids)
    out.update(stats)
    return out


def under_withdrawal(db: Session, farm_ids: list[int] | None) -> list[dict]:
    rows = []
    if farm_ids is None:
        farms = db.execute(select(Animal.farm_id).distinct()).scalars().all()
        farm_ids = list(farms)
    for fid in farm_ids:
        rows.extend(farm_compliance(db, fid))
    return [r for r in rows if r["under_withdrawal"]]


def recent_violations(db: Session, farm_ids: list[int] | None, days: int = 30) -> list[dict]:
    cutoff = ensure_aware(utcnow()) - timedelta(days=days)
    stmt = (
        select(SaleEvent, Animal)
        .outerjoin(Animal, SaleEvent.animal_id == Animal.id)
        .where(SaleEvent.is_violation.is_(True), SaleEvent.occurred_at > cutoff)
        .order_by(SaleEvent.occurred_at.desc())
    )
    if farm_ids is not None:
        stmt = stmt.where(SaleEvent.farm_id.in_(farm_ids or [-1]))
    return [
        {
            "animal_tag": a.tag_id if a else "(bulk)",
            "product": s.product_type.value,
            "quantity": f"{s.quantity} {s.unit}",
            "occurred": ist_str(s.occurred_at) if s.occurred_at else "?",
            "linked_administration_ids": s.linked_administration_ids or [],
        }
        for s, a in db.execute(stmt).all()
    ]


def amu_stats(db: Session, farm_ids: list[int] | None, months: int = 3) -> dict:
    return {
        "aware_breakdown": analytics_service.aware_breakdown(db, farm_ids, months=months),
        "leaderboard": analytics_service.drug_leaderboard(db, farm_ids, limit=5),
        "monthly_trend": analytics_service.monthly_trend(db, farm_ids, months=months)[-6:],
    }


def animal_history(db: Session, tag_id: str, farm_ids: list[int] | None) -> dict | None:
    stmt = select(Animal).where(Animal.tag_id == tag_id.strip().upper())
    if farm_ids is not None:
        stmt = stmt.where(Animal.farm_id.in_(farm_ids or [-1]))
    animal = db.execute(stmt).scalars().first()
    if not animal:
        return None
    admins = db.execute(
        select(Administration, Drug)
        .join(Drug, Administration.drug_id == Drug.id)
        .where(Administration.animal_id == animal.id)
        .order_by(Administration.started_at.desc())
        .limit(10)
    ).all()
    status_rows = [r for r in under_withdrawal(db, [animal.farm_id]) if r["tag_id"] == animal.tag_id]
    return {
        "tag_id": animal.tag_id,
        "species": animal.species.value,
        "breed": animal.breed,
        "production_status": animal.production_status.value,
        "under_withdrawal_now": bool(status_rows),
        "withdrawal_tissues": status_rows[0]["tissues"] if status_rows else [],
        "recent_treatments": [
            {
                "drug": d.generic_name,
                "aware_class": d.aware_class.value,
                "supervised": adm.prescription_id is not None,
                "started": ist_str(adm.started_at) if adm.started_at else "?",
                "course_days": adm.course_days,
            }
            for adm, d in admins
        ],
        "violations": recent_violations_for_animal(db, animal.id),
    }


def recent_violations_for_animal(db: Session, animal_id: int) -> list[dict]:
    sales = db.execute(
        select(SaleEvent).where(SaleEvent.animal_id == animal_id, SaleEvent.is_violation.is_(True))
    ).scalars().all()
    return [
        {"product": s.product_type.value, "occurred": ist_str(s.occurred_at) if s.occurred_at else "?"}
        for s in sales
    ]


def open_alerts(db: Session, farm_ids: list[int] | None, limit: int = 8) -> list[dict]:
    stmt = select(Alert).where(Alert.resolved_at.is_(None)).order_by(Alert.created_at.desc()).limit(limit)
    if farm_ids is not None:
        stmt = stmt.where(Alert.farm_id.in_(farm_ids or [-1]))
    alerts = db.execute(stmt).scalars().all()
    order = {"critical": 0, "warning": 1, "info": 2}
    return sorted(
        [
            {
                "severity": a.severity.value,
                "type": a.type.value,
                "title": a.title,
                "message": a.message,
            }
            for a in alerts
        ],
        key=lambda x: order.get(x["severity"], 3),
    )


def risk_watchlist(db: Session, farm_ids: list[int] | None, limit: int = 5) -> list[dict]:
    from app.services.ml import features as feat
    from app.services.ml import serve

    stmt = select(Animal).where(Animal.status == "active")
    if farm_ids is not None:
        stmt = stmt.where(Animal.farm_id.in_(farm_ids or [-1]))
    animals = db.execute(stmt.limit(60)).scalars().all()
    scored = []
    for a in animals:
        pred = serve.predict_mrl(feat.mrl_features(db, a))
        if pred:
            scored.append({"tag_id": a.tag_id, "risk": pred["risk"], "band": pred["band"]})
    scored.sort(key=lambda r: -r["risk"])
    return scored[:limit]


TOOL_SCHEMAS = [
    {
        "name": "get_farm_compliance_summary",
        "description": "Overall stats: active animals, treatments last 30d, supervised share, total violations, open critical alerts.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_animals_under_withdrawal",
        "description": "Animals currently inside an antimicrobial withdrawal window, with tissue countdowns.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_recent_violations",
        "description": "MRL violation sales within the last N days (default 30).",
        "input_schema": {
            "type": "object",
            "properties": {"days": {"type": "integer", "description": "lookback window"}},
        },
    },
    {
        "name": "get_amu_stats",
        "description": "Antimicrobial usage analytics: WHO AWaRe breakdown, most-used drugs, monthly trend.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_animal_history",
        "description": "Full record of one animal by its ear-tag (e.g. 'MUR-0017'): withdrawal status, recent treatments, violations.",
        "input_schema": {
            "type": "object",
            "properties": {"tag_id": {"type": "string", "description": "ear-tag like MUR-0017"}},
            "required": ["tag_id"],
        },
    },
    {
        "name": "get_open_alerts",
        "description": "Current unresolved alerts (violations, prohibited drugs, sensor anomalies, upcoming clearances).",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "predict_animal_risk",
        "description": "Top ML-ranked animals by predicted MRL-violation risk.",
        "input_schema": {"type": "object", "properties": {}},
    },
]

TOOL_FUNCS = {
    "get_farm_compliance_summary": lambda db, farm_ids, args: compliance_summary(db, farm_ids),
    "list_animals_under_withdrawal": lambda db, farm_ids, args: under_withdrawal(db, farm_ids),
    "get_recent_violations": lambda db, farm_ids, args: recent_violations(
        db, farm_ids, days=int(args.get("days", 30))
    ),
    "get_amu_stats": lambda db, farm_ids, args: amu_stats(db, farm_ids),
    "get_animal_history": lambda db, farm_ids, args: animal_history(db, args.get("tag_id", ""), farm_ids),
    "get_open_alerts": lambda db, farm_ids, args: open_alerts(db, farm_ids),
    "predict_animal_risk": lambda db, farm_ids, args: risk_watchlist(db, farm_ids),
}
