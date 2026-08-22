from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import ensure_farm_access, farmer_or_admin, get_current_user, scoped_farm_ids
from app.db.session import get_db
from app.models import Animal, SaleEvent, User
from app.models.enums import AlertSeverity, AlertType, LedgerEventType, SaleProduct
from app.schemas import SaleEventIn
from app.services import alert_service, ledger_service
from app.services.mrl_engine import (
    enforceable_windows,
    enforceable_windows_for_animal,
    evaluate_sale,
    ist_str,
)
from app.utils.timeutil import timedelta, utcnow

router = APIRouter(prefix="/sale-events", tags=["sales"])


@router.post("")
def create_sale(
    payload: SaleEventIn,
    db: Session = Depends(get_db),
    user: User = Depends(farmer_or_admin),
):
    """Record a milk/meat/eggs/live-animal sale.

    The engine freezes the compliance verdict at insert time (evidence), raises
    R1/R3 alerts when needed, and appends a ledger entry -- one transaction.
    """
    if user.farm_id is None:
        raise HTTPException(400, "User has no farm")
    farm_id = user.farm_id

    animal = db.get(Animal, payload.animal_id) if payload.animal_id else None
    if payload.animal_id and not animal:
        raise HTTPException(404, "Animal not found")
    if animal:
        ensure_farm_access(user, animal.farm_id)

    occurred_at = payload.occurred_at or utcnow()

    # Bulk milk/eggs without an animal: check the WHOLE herd's enforceable windows.
    if animal is not None:
        windows = enforceable_windows_for_animal(db, animal.id)
    else:
        herd = db.execute(
            select(Animal.id).where(Animal.farm_id == farm_id, Animal.status == "active")
        ).scalars().all()
        windows = enforceable_windows(db, list(herd))

    product = payload.product_type
    if product in (SaleProduct.milk, SaleProduct.meat, SaleProduct.eggs, SaleProduct.live_animal):
        verdict = evaluate_sale(product, windows, occurred_at)
    else:  # pragma: no cover
        verdict = evaluate_sale(product, [], occurred_at)

    warned = bool(verdict.violating_windows) or verdict.was_under_withdrawal
    if warned and not payload.acknowledge_warning:
        return {
            "warning": True,
            "message": (
                f"{product.value} is currently under withdrawal"
                + (f" ({verdict.hours_premature}h premature at sale time)" if verdict.hours_premature else "")
                + ". Confirming will log this as an MRL violation."
            ),
            "violating": [
                {
                    "tissue": w.tissue.value,
                    "drug_name": w.drug_name,
                    "clears_at": w.clears_at.isoformat(),
                    "administration_id": w.administration_id,
                }
                for w in verdict.violating_windows
            ],
        }

    unit = payload.unit or {SaleProduct.milk: "litres", SaleProduct.meat: "kg",
                            SaleProduct.eggs: "trays", SaleProduct.live_animal: "birds"}[product]
    sale = SaleEvent(
        farm_id=farm_id,
        animal_id=animal.id if animal else None,
        product_type=product,
        quantity=payload.quantity,
        unit=unit,
        buyer_name=payload.buyer_name,
        buyer_type=payload.buyer_type,
        occurred_at=occurred_at,
        was_under_withdrawal=verdict.was_under_withdrawal,
        is_violation=verdict.is_violation,
        linked_administration_ids=verdict.linked_administration_ids,
        amount_inr=payload.amount_inr,
        notes=payload.notes,
    )
    db.add(sale)
    db.flush()

    alerts_raised = []
    if verdict.is_violation:
        drug_names = ", ".join(sorted({w.drug_name or "?" for w in verdict.violating_windows}))
        tissue_label = {"milk": "milk", "meat": "meat", "eggs": "eggs"}[
            product.value if product != SaleProduct.live_animal else "meat"
        ]
        alert = alert_service.create_alert(
            db,
            farm_id=farm_id,
            animal_id=animal.id if animal else None,
            type_=AlertType.MRL_VIOLATION,
            severity=AlertSeverity.critical,
            title=(
                f"MRL VIOLATION: {tissue_label} sold while under withdrawal"
                + (f" ({animal.tag_id})" if animal else "")
            ),
            message=(
                f"{payload.quantity} {unit} of {tissue_label} was sold on "
                f"{ist_str(occurred_at)} while still within the withdrawal period for "
                f"{drug_names} ({verdict.hours_premature} h premature). Residue above MRL "
                f"is likely. Linked administrations: {verdict.linked_administration_ids}. "
                f"Laboratory testing and regulatory notification recommended."
            ),
            related_type="sale_event",
            related_id=sale.id,
        )
        alerts_raised.append(alert.type.value)
    elif verdict.near_miss:
        alert_service.create_alert(
            db,
            farm_id=farm_id,
            animal_id=animal.id if animal else None,
            type_=AlertType.NEAR_MISS_SALE,
            severity=AlertSeverity.info,
            title="Near-miss sale within 24h of clearance",
            message=(
                f"A sale was recorded within 24 hours after withdrawal clearance. "
                f"No violation, but plan sales with a safety buffer."
            ),
            related_type="sale_event",
            related_id=sale.id,
            dedupe_window=timedelta(hours=24),
        )
        alerts_raised.append("NEAR_MISS_SALE")

    ledger_service.append_event(
        db,
        LedgerEventType.sale_event,
        sale.id,
        {
            "sale_event_id": sale.id,
            "animal_tag": animal.tag_id if animal else None,
            "product_type": product.value,
            "quantity": payload.quantity,
            "unit": unit,
            "occurred_at": occurred_at.isoformat(),
            "was_under_withdrawal": sale.was_under_withdrawal,
            "is_violation": sale.is_violation,
            "linked_administration_ids": sale.linked_administration_ids,
        },
        actor_user_id=user.id,
    )
    db.commit()

    return {
        "id": sale.id,
        "is_violation": sale.is_violation,
        "was_under_withdrawal": sale.was_under_withdrawal,
        "alerts_raised": alerts_raised,
    }


@router.get("")
def list_sales(
    farm_id: int | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = (
        select(SaleEvent, Animal)
        .outerjoin(Animal, SaleEvent.animal_id == Animal.id)
        .order_by(SaleEvent.occurred_at.desc())
        .limit(limit)
    )
    allowed = scoped_farm_ids(user)
    if allowed is not None:
        stmt = stmt.where(SaleEvent.farm_id.in_(allowed or [-1]))
    elif farm_id is not None:
        stmt = stmt.where(SaleEvent.farm_id == farm_id)
    rows = db.execute(stmt).all()
    return [
        {
            "id": s.id,
            "farm_id": s.farm_id,
            "animal_tag": a.tag_id if a else None,
            "product_type": s.product_type.value,
            "quantity": s.quantity,
            "unit": s.unit,
            "buyer_name": s.buyer_name,
            "was_under_withdrawal": s.was_under_withdrawal,
            "is_violation": s.is_violation,
            "amount_inr": s.amount_inr,
            "occurred_at": s.occurred_at.isoformat() if s.occurred_at else None,
        }
        for s, a in rows
    ]
