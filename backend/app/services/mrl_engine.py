"""MRL compliance engine -- the core of PashuSafe.

Pure functions first (unit-testable without a DB), then thin DB adapters used
by the routers. Conventions:

* A treatment course opens one unsafe interval per applicable tissue.
* Interval START = FIRST dose of the course (`administration.started_at`) --
  milk/meat/eggs produced DURING treatment are already contaminated.
* Interval END   = clearance: end of the Nth full IST calendar day after the
  LAST dose, N = ceil(labelled withdrawal period in days)  (safe side).
* Overlapping/stacked drugs collapse per tissue to the LONGEST interval end.
* An animal is compliant only when every currently-producing tissue is clear;
  the binding constraint is the latest per-tissue clearance.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Administration, Animal, Drug, DrugSpeciesRule, WithdrawalPeriod
from app.models.enums import (
    AlertSeverity,
    AlertType,
    ProductionStatus,
    SaleProduct,
    Species,
    Tissue,
    WithdrawalStatus,
)
from app.utils.timeutil import as_ist, ensure_aware, ist_str, utcnow, withdrawal_clears_at

DAIRY_SPECIES = {Species.cattle, Species.buffalo, Species.goat, Species.sheep}
NEAR_MISS_WINDOW = timedelta(hours=24)


# --------------------------------------------------------------------------- #
# Pure core
# --------------------------------------------------------------------------- #

@dataclass
class WindowInfo:
    tissue: Tissue
    starts_at: datetime
    clears_at: datetime
    administration_id: int
    drug_name: str | None = None
    animal_id: int | None = None


@dataclass
class ComplianceStatus:
    overall: str  # CLEAR | CLEAR_TODAY | WITHDRAWAL_ACTIVE
    tissues: list[dict] = field(default_factory=list)
    next_clearance: datetime | None = None

    @property
    def under_withdrawal(self) -> bool:
        return self.overall == "WITHDRAWAL_ACTIVE"


def applicable_tissues(species: Species, production_status: ProductionStatus) -> list[Tissue]:
    """Which residue-bearing tissues this animal is currently producing."""
    tissues = [Tissue.meat]
    if species in DAIRY_SPECIES and production_status == ProductionStatus.lactating:
        tissues.append(Tissue.milk)
    if species == Species.poultry and production_status == ProductionStatus.laying:
        tissues.append(Tissue.eggs)
    return tissues


def build_withdrawal_rows(
    species: Species,
    production_status: ProductionStatus,
    started_at: datetime,
    last_dose_at: datetime,
    rule: DrugSpeciesRule | None,
) -> list[WithdrawalPeriod]:
    """Materialized WithdrawalPeriod rows for one administration (not yet persisted).

    starts_at = course start (unsafe from first dose); clears_at derives from the
    LAST dose + labelled withdrawal period.
    """
    if rule is None:
        return []
    rows: list[WithdrawalPeriod] = []
    for tissue in applicable_tissues(species, production_status):
        wp_days = {
            Tissue.milk: rule.withdrawal_milk_days,
            Tissue.meat: rule.withdrawal_meat_days,
            Tissue.eggs: rule.withdrawal_eggs_days,
        }[tissue]
        if wp_days is None:  # tissue not regulated for this drug/species pair
            continue
        rows.append(
            WithdrawalPeriod(
                tissue=tissue,
                starts_at=started_at,
                clears_at=withdrawal_clears_at(last_dose_at, wp_days),
                status=WithdrawalStatus.active,
            )
        )
    return rows


def summarize_windows(rows: list[WindowInfo], now: datetime | None = None) -> ComplianceStatus:
    """Collapse windows per tissue (max clears_at) and derive overall status."""
    now = ensure_aware(now or utcnow())
    binding: dict[Tissue, WindowInfo] = {}
    for w in rows:
        if w.clears_at <= now:  # already over; treat as cleared
            continue
        cur = binding.get(w.tissue)
        if cur is None or w.clears_at > cur.clears_at:
            binding[w.tissue] = w

    tissues: list[dict] = []
    for tissue, w in sorted(binding.items(), key=lambda kv: kv[1].clears_at):
        remaining = w.clears_at - now
        tissues.append(
            {
                "tissue": tissue.value,
                "clears_at": w.clears_at,
                "countdown": f"{remaining.days}d {remaining.seconds // 3600}h",
                "drug_name": w.drug_name,
                "administration_id": w.administration_id,
            }
        )

    if binding:
        soonest = min(w.clears_at for w in binding.values())
        overall = "CLEAR_TODAY" if soonest - now <= timedelta(hours=24) else "WITHDRAWAL_ACTIVE"
        next_clearance = soonest
    else:
        overall, next_clearance = "CLEAR", None
    return ComplianceStatus(overall=overall, tissues=tissues, next_clearance=next_clearance)


def product_to_tissue(product: SaleProduct) -> Tissue | None:
    return {
        SaleProduct.milk: Tissue.milk,
        SaleProduct.meat: Tissue.meat,
        SaleProduct.live_animal: Tissue.meat,  # slaughter-bound transfer
        SaleProduct.eggs: Tissue.eggs,
    }.get(product)


@dataclass
class SaleVerdict:
    is_violation: bool
    was_under_withdrawal: bool
    violating_windows: list[WindowInfo]
    near_miss: bool
    hours_premature: float | None = None
    linked_administration_ids: list[int] = field(default_factory=list)


def evaluate_sale(
    product: SaleProduct, windows: list[WindowInfo], occurred_at: datetime
) -> SaleVerdict:
    """Rule R1 (hard violation) + R3 (near miss) against windows active at sale time."""
    when = ensure_aware(occurred_at)
    tissue = product_to_tissue(product)
    relevant = [w for w in windows if w.tissue == tissue] if tissue else []

    violating = [
        w for w in relevant
        if ensure_aware(w.starts_at) <= when < ensure_aware(w.clears_at)
    ]
    near_miss = False
    hours_premature: float | None = None
    if violating:
        worst = max(violating, key=lambda w: w.clears_at)
        hours_premature = round((ensure_aware(worst.clears_at) - when).total_seconds() / 3600, 1)
    elif relevant:
        earliest_clear = min(ensure_aware(w.clears_at) for w in relevant)
        late_by = when - earliest_clear
        near_miss = timedelta(0) <= late_by <= NEAR_MISS_WINDOW

    return SaleVerdict(
        is_violation=bool(violating),
        was_under_withdrawal=bool(violating),
        violating_windows=violating,
        near_miss=near_miss,
        hours_premature=hours_premature,
        linked_administration_ids=sorted({w.administration_id for w in violating}),
    )


# --------------------------------------------------------------------------- #
# DB adapters
# --------------------------------------------------------------------------- #

def get_rule(db: Session, drug_id: int, species: Species) -> DrugSpeciesRule | None:
    return db.execute(
        select(DrugSpeciesRule).where(
            DrugSpeciesRule.drug_id == drug_id, DrugSpeciesRule.species == species
        )
    ).scalar_one_or_none()


def record_administration(
    db: Session,
    *,
    animal: Animal,
    drug: Drug,
    started_at: datetime,
    course_days: int,
    dose_amount: float,
    route,
    prescription_id: int | None = None,
    administered_by_user_id: int | None = None,
    batch_number: str | None = None,
    cost_inr: float | None = None,
    notes: str | None = None,
) -> tuple[Administration, list[WithdrawalPeriod]]:
    """Create an administration + its withdrawal rows (caller commits).

    Raises ValueError on unknown (drug, species) formulary pair -- EXCEPT for
    food-chain-prohibited drugs, which record with zero withdrawal rows so the
    R2 guard can raise a PROHIBITED_DRUG_USED alert instead of swallowing the
    event behind a validation error.
    """
    rule = get_rule(db, drug.id, animal.species)
    if rule is None and not drug.prohibited_in_food_animals:
        raise ValueError(
            f"{drug.generic_name} has no formulary rule for species '{animal.species.value}'"
        )
    admin = Administration(
        animal_id=animal.id,
        drug_id=drug.id,
        prescription_id=prescription_id,
        administered_by_user_id=administered_by_user_id,
        started_at=started_at,
        course_days=course_days,
        dose_amount=dose_amount,
        route=route,
        batch_number=batch_number,
        cost_inr=cost_inr,
        notes=notes,
    )
    admin.compute_last_dose()
    db.add(admin)
    db.flush()  # assign id

    rows = (
        build_withdrawal_rows(
            animal.species,
            animal.production_status,
            admin.started_at,
            admin.last_dose_at,
            rule,
        )
        if rule is not None
        else []
    )
    for r in rows:
        r.administration_id = admin.id
        db.add(r)
    db.flush()
    return admin, rows


def load_open_windows(db: Session, animal_ids: list[int], now: datetime) -> list[WindowInfo]:
    """All not-yet-expired withdrawal windows for the given animals."""
    if not animal_ids:
        return []
    stmt = (
        select(WithdrawalPeriod, Administration, Drug)
        .join(Administration, WithdrawalPeriod.administration_id == Administration.id)
        .join(Drug, Administration.drug_id == Drug.id)
        .where(
            Administration.animal_id.in_(animal_ids),
            WithdrawalPeriod.status == WithdrawalStatus.active,
            WithdrawalPeriod.clears_at > now,
        )
    )
    return [
        WindowInfo(
            tissue=wp.tissue,
            starts_at=ensure_aware(wp.starts_at),
            clears_at=ensure_aware(wp.clears_at),
            administration_id=wp.administration_id,
            drug_name=drug.generic_name,
            animal_id=adm.animal_id,
        )
        for wp, adm, drug in db.execute(stmt).all()
    ]


def enforceable_windows(db: Session, animal_ids: list[int]) -> list[WindowInfo]:
    """All ACTIVE windows regardless of expiry -- for retroactive sale checks.

    Windows flipped to 'cleared' by lab evidence are excluded on purpose: a
    proven-safe sale is not a violation even if it fell inside the theoretical
    withdrawal window.
    """
    if not animal_ids:
        return []
    stmt = (
        select(WithdrawalPeriod, Administration, Drug)
        .join(Administration, WithdrawalPeriod.administration_id == Administration.id)
        .join(Drug, Administration.drug_id == Drug.id)
        .where(
            Administration.animal_id.in_(animal_ids),
            WithdrawalPeriod.status == WithdrawalStatus.active,
        )
    )
    return [
        WindowInfo(
            tissue=wp.tissue,
            starts_at=ensure_aware(wp.starts_at),
            clears_at=ensure_aware(wp.clears_at),
            administration_id=wp.administration_id,
            drug_name=drug.generic_name,
            animal_id=adm.animal_id,
        )
        for wp, adm, drug in db.execute(stmt).all()
    ]


def enforceable_windows_for_animal(db: Session, animal_id: int) -> list[WindowInfo]:
    return [w for w in enforceable_windows(db, [animal_id]) if w.animal_id == animal_id]


def animal_compliance(db: Session, animal: Animal, now: datetime | None = None) -> dict:
    now = ensure_aware(now or utcnow())
    status = summarize_windows(load_open_windows(db, [animal.id], now), now)
    return {
        "animal_id": animal.id,
        "tag_id": animal.tag_id,
        "species": animal.species.value,
        "production_status": animal.production_status.value,
        "overall": status.overall,
        "under_withdrawal": status.under_withdrawal,
        "tissues": [
            {**t, "clears_at": t["clears_at"].isoformat(),
             "clears_at_display": ist_str(t["clears_at"])}
            for t in status.tissues
        ],
        "next_clearance": status.next_clearance.isoformat() if status.next_clearance else None,
    }


def farm_compliance(db: Session, farm_id: int, now: datetime | None = None) -> list[dict]:
    now = ensure_aware(now or utcnow())
    animals = db.execute(
        select(Animal).where(Animal.farm_id == farm_id, Animal.status == "active")
    ).scalars().all()
    windows = load_open_windows(db, [a.id for a in animals], now)

    out: list[dict] = []
    for animal in animals:
        mine = [w for w in windows if w.animal_id == animal.id]
        status = summarize_windows(mine, now)
        out.append(
            {
                "animal_id": animal.id,
                "tag_id": animal.tag_id,
                "species": animal.species.value,
                "breed": animal.breed,
                "production_status": animal.production_status.value,
                "overall": status.overall,
                "under_withdrawal": status.under_withdrawal,
                "tissues": [
                    {**t, "clears_at": t["clears_at"].isoformat(),
                     "clears_at_display": ist_str(t["clears_at"])}
                    for t in status.tissues
                ],
                "next_clearance": (
                    status.next_clearance.isoformat() if status.next_clearance else None
                ),
            }
        )
    out.sort(key=lambda r: (r["overall"] != "WITHDRAWAL_ACTIVE", r["next_clearance"] or "9999"))
    return out


def violation_report(db: Session, farm_ids: list[int] | None, limit: int = 200) -> list[dict]:
    from app.models import SaleEvent

    stmt = (
        select(SaleEvent)
        .options(selectinload(SaleEvent.animal))
        .where(SaleEvent.is_violation.is_(True))
        .order_by(SaleEvent.occurred_at.desc())
        .limit(limit)
    )
    if farm_ids is not None:
        stmt = stmt.where(SaleEvent.farm_id.in_(farm_ids))
    out = []
    for s in db.execute(stmt).scalars().all():
        out.append(
            {
                "sale_event_id": s.id,
                "farm_id": s.farm_id,
                "animal_tag": s.animal.tag_id if s.animal else None,
                "product_type": s.product_type.value,
                "quantity": s.quantity,
                "unit": s.unit,
                "buyer_name": s.buyer_name,
                "occurred_at": s.occurred_at.isoformat() if s.occurred_at else None,
                "hours_premature_hours": None,  # filled by caller from alert if needed
                "linked_administration_ids": s.linked_administration_ids or [],
            }
        )
    return out
