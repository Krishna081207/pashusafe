import csv
import io

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, scoped_farm_ids
from app.db.session import get_db
from app.models import Farm, User
from app.services import analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/compliance/by-farm")
def compliance_by_farm(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Per-farm compliance scoreboard (worst first) -- regulator/admin view."""
    allowed = scoped_farm_ids(user)
    stmt = select(Farm).order_by(Farm.id)
    if allowed is not None:
        stmt = stmt.where(Farm.id.in_(allowed or [-1]))
    farms = db.execute(stmt).scalars().all()

    rows = []
    for f in farms:
        s = analytics_service.dashboard_stats(db, [f.id])
        rows.append(
            {
                "farm_id": f.id,
                "name": f.name,
                "district": f.district,
                "state": f.state,
                **s,
            }
        )
    rows.sort(
        key=lambda r: (-r["violations_total"], -r["critical_alerts_open"], r["name"])
    )
    return rows


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return analytics_service.dashboard_stats(db, scoped_farm_ids(user))


@router.get("/amu")
def amu_analytics(
    months: int = 6,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    farm_ids = scoped_farm_ids(user)
    return {
        "aware_breakdown": analytics_service.aware_breakdown(db, farm_ids, months=months),
        "drug_leaderboard": analytics_service.drug_leaderboard(db, farm_ids),
        "monthly_trend": analytics_service.monthly_trend(db, farm_ids, months=months),
    }


@router.get("/sales")
def sales_analytics(
    months: int = 6,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Animal-product sales: monthly volumes (milk/eggs/meat), revenue and
    clean-vs-violating sale split."""
    return analytics_service.sales_analytics(db, scoped_farm_ids(user), months=months)


@router.get("/report/monthly")
def monthly_report(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Printable JSON report (regulators / FPO review meetings)."""
    return analytics_service.monthly_report(db, scoped_farm_ids(user))


@router.get("/export.csv")
def export_csv(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from sqlalchemy import select

    from app.models import Administration, Animal, Drug

    farm_ids = scoped_farm_ids(user)
    stmt = (
        select(Administration, Animal, Drug)
        .join(Animal, Administration.animal_id == Animal.id)
        .join(Drug, Administration.drug_id == Drug.id)
        .order_by(Administration.started_at.desc())
        .limit(5000)
    )
    if farm_ids is not None:
        stmt = stmt.where(Animal.farm_id.in_(farm_ids or [-1]))

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        ["administration_id", "farm_id", "animal_tag", "drug", "aware_class",
         "dose_mg_kg", "route", "course_days", "started_at", "supervised"]
    )
    for adm, animal, drug in db.execute(stmt).all():
        writer.writerow(
            [adm.id, animal.farm_id, animal.tag_id, drug.generic_name,
             drug.aware_class.value, adm.dose_amount, adm.route.value,
             adm.course_days,
             adm.started_at.isoformat() if adm.started_at else "",
             bool(adm.prescription_id)]
        )
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=pashusafe_amu_export.csv"},
    )
