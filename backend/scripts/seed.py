#!/usr/bin/env python3
"""PashuSafe demo seeder.

    python scripts/seed.py

Drops + recreates the schema, loads the drug formulary, creates demo users /
farms / animals, generates ~150 days of realistic treatment & sale history with
scripted scenarios, then trains the ML models. Deterministic (fixed RNG).

Prints the demo credentials at the end.
"""

import json
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

# allow `python scripts/seed.py` from backend/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.models import (  # noqa: E402
    Administration,
    Alert,
    Animal,
    Drug,
    DrugSpeciesRule,
    Farm,
    Prescription,
    ResidueTest,
    SaleEvent,
    SensorReading,
    TraceLedgerEntry,
    User,
)
from app.db.base import Base  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.enums import (  # noqa: E402
    AlertSeverity,
    AlertType,
    AWaReClass,
    BuyerType,
    LedgerEventType,
    ProductionStatus,
    ResidueResult,
    Role,
    Route,
    SaleProduct,
    Sex,
    Species,
)
from app.services import alert_service, iot_simulator  # noqa: E402
from app.services.ledger_service import append_event  # noqa: E402
from app.services.ml.train import train_all  # noqa: E402
from app.services.mrl_engine import (  # noqa: E402
    build_withdrawal_rows,
    enforceable_windows_for_animal,
    evaluate_sale,
    get_rule,
    ist_str,
    record_administration,
)
from app.utils.timeutil import ensure_aware, utcnow, withdrawal_clears_at  # noqa: E402

RNG = random.Random(42)
NOW = ensure_aware(utcnow())
DEMO_PASSWORD = "Demo@1234"

BASE_DIR = Path(__file__).resolve().parents[1]
DRUGS_JSON = BASE_DIR / "seed_data" / "drugs.json"

TYPICAL_DOSE = {  # mg/kg per dose (approximate label doses for demo)
    "Enrofloxacin": 7.5, "Oxytetracycline": 10.0, "Amoxicillin": 10.0,
    "Cefalexin": 10.0, "Gentamicin": 6.0, "Sulfadiazine + Trimethoprim": 24.0,
    "Tylosin": 10.0, "Florfenicol": 20.0, "Benzylpenicillin": 12.0,
    "Streptomycin": 10.0, "Doxycycline": 10.0, "Marbofloxacin": 2.0,
    "Colistin": 5.0, "Cefoperazone": 10.0, "Ciprofloxacin": 7.5,
    "Neomycin": 10.0, "Tiamulin": 12.0, "Danofloxacin": 6.0,
}

DIAGNOSES = ["Mastitis", "FMD suspected", "Metritis", "Respiratory infection",
             "Diarrhoea", "Foot rot", "Brucellosis suspect", "Eye infection",
             "Wound infection", "Fever of unknown origin"]

FARMS = [
    dict(name="Sri Venkateswara Dairy", village="Napad", district="Anand",
         state="Gujarat", pincode="388001", latitude=22.57, longitude=72.95),
    dict(name="Green Valley Poultry", village="Pudur", district="Namakkal",
         state="Tamil Nadu", pincode="637001", latitude=11.22, longitude=78.17),
    dict(name="Shakti Dairy Collective", village="Nilokheri", district="Karnal",
         state="Haryana", pincode="132117", latitude=29.83, longitude=76.93),
    dict(name="Punjab Piggery Farm", village="Jagraon", district="Ludhiana",
         state="Punjab", pincode="142026", latitude=30.79, longitude=75.48),
    dict(name="Bengal Goat Cooperative", village="Amdanga", district="North 24 Parganas",
         state="West Bengal", pincode="743221", latitude=22.85, longitude=88.55),
]

USERS = [
    ("Ravi Patel", "ravi@demo.in", Role.farmer, 1),
    ("Sunita Krishnan", "sunita@demo.in", Role.farmer, 2),
    ("Manoj Chaudhary", "manoj@demo.in", Role.farmer, 3),
    ("Harpreet Singh", "harpreet@demo.in", Role.farmer, 4),
    ("Aisha Khan", "aisha@demo.in", Role.farmer, 5),
    ("Dr. Priya Nair", "dr.priya@demo.in", Role.vet, None),
    ("Food Safety Inspector", "inspector@fssai-demo.in", Role.regulator, None),
    ("System Admin", "admin@demo.in", Role.admin, None),
]

HERDS = [
    # farm_idx, [(species, breed_prefix, breeds, production_status), count]
    (1, Species.cattle, ["Gir", "Sahiwal", "Tharparkar"], ProductionStatus.lactating, 10, "GIR"),
    (1, Species.buffalo, ["Murrah", "Mehsana"], ProductionStatus.lactating, 8, "MUR"),
    (1, Species.cattle, ["Gir"], ProductionStatus.growing, 3, "CAL"),
    (2, Species.poultry, ["Vanaraja", "Giriraja"], ProductionStatus.laying, 18, "VAN"),
    (3, Species.cattle, ["Sahiwal", "Tharparkar", "Gir"], ProductionStatus.lactating, 14, "SAH"),
    (4, Species.pig, ["Large White Yorkshire"], ProductionStatus.fattening, 8, "LWH"),
    (5, Species.goat, ["Jamunapari", "Barbari", "Black Bengal"], ProductionStatus.lactating, 9, "JAM"),
]

WATCH_HEAVY = ["Enrofloxacin", "Ciprofloxacin", "Danofloxacin", "Marbofloxacin",
               "Gentamicin", "Cefoperazone"]


def load_formulary(db) -> dict[str, Drug]:
    data = json.loads(DRUGS_JSON.read_text())
    drugs: dict[str, Drug] = {}
    for entry in data:
        drug = Drug(
            generic_name=entry["generic_name"],
            active_ingredient=entry.get("active_ingredient"),
            drug_class=entry["drug_class"],
            aware_class=AWaReClass(entry["aware_class"]),
            prohibited_in_food_animals=entry.get("prohibited_in_food_animals", False),
            prohibited_in_lactating_animals=entry.get("prohibited_in_lactating_animals", False),
            notes=entry.get("notes"),
        )
        db.add(drug)
        db.flush()
        for r in entry.get("rules", []):
            db.add(DrugSpeciesRule(
                drug_id=drug.id,
                species=Species(r["species"]),
                withdrawal_milk_days=r["withdrawal_milk_days"],
                withdrawal_meat_days=r["withdrawal_meat_days"],
                withdrawal_eggs_days=r["withdrawal_eggs_days"],
                mrl_milk_ug_kg=r["mrl_milk_ug_kg"],
                mrl_meat_ug_kg=r["mrl_meat_ug_kg"],
                mrl_eggs_ug_kg=r["mrl_eggs_ug_kg"],
            ))
        drugs[drug.generic_name] = drug
    return drugs


def create_farms_users(db) -> tuple[list[Farm], list[User]]:
    farms = []
    for f in FARMS:
        farm = Farm(**f)
        db.add(farm)
        farms.append(farm)
    db.flush()
    users = []
    for name, email, role, farm_idx in USERS:
        user = User(
            full_name=name, email=email,
            password_hash=hash_password(DEMO_PASSWORD),
            role=role,
            farm_id=farms[farm_idx - 1].id if farm_idx else None,
            phone=f"+91-9{RNG.randint(100000000, 999999999)}",
        )
        db.add(user)
        users.append(user)
    db.flush()
    return farms, users


def create_herds(db, farms: list[Farm]) -> list[Animal]:
    animals: list[Animal] = []
    for farm_idx, species, breeds, prod_status, count, prefix in HERDS:
        for i in range(1, count + 1):
            age_years = RNG.uniform(1.5, 8) if prod_status != ProductionStatus.growing else RNG.uniform(0.4, 1.0)
            weight = {
                Species.cattle: RNG.uniform(280, 480),
                Species.buffalo: RNG.uniform(350, 550),
                Species.poultry: RNG.uniform(1.8, 2.8),
                Species.pig: RNG.uniform(60, 110),
                Species.goat: RNG.uniform(28, 55),
            }[species]
            animal = Animal(
                farm_id=farms[farm_idx - 1].id,
                tag_id=f"{prefix}-{i:03d}",
                species=species,
                breed=RNG.choice(breeds),
                sex=Sex.male if species == Species.pig and i % 4 == 0 else Sex.female,
                birth_date=(NOW - timedelta(days=int(age_years * 365))).date(),
                production_status=prod_status,
                weight_kg=round(weight, 1),
                scenario_tag=None,
            )
            db.add(animal)
            animals.append(animal)
    db.flush()
    return animals


def vet_user(users: list[User]) -> User:
    return next(u for u in users if u.role == Role.vet)


def generate_history(db, farms, users, animals, drugs):
    vet = vet_user(users)
    farm_rate = {1: 1.0, 2: 0.8, 3: 2.6, 4: 1.1, 5: 0.9}   # F3 = chronic high-use
    supervision = {1: 0.65, 2: 0.55, 3: 0.25, 4: 0.5, 5: 0.6}
    watch_bias = {3: 0.55}                                  # F3 prefers Watch drugs

    by_farm: dict[int, list[Animal]] = {}
    for a in animals:
        by_farm.setdefault(a.farm_id, []).append(a)

    stats = {"administrations": 0, "prescriptions": 0, "sales": 0, "violations": 0}

    def pick_drug(farm_idx: int, animal: Animal) -> Drug:
        usable = [
            d for d in drugs.values()
            if any(r.species == animal.species for r in d.rules)
        ]
        bias = watch_bias.get(farm_idx, 0.15)
        watch_pool = [d for d in usable if d.aware_class == AWaReClass.Watch]
        access_pool = [d for d in usable if d.aware_class == AWaReClass.Access]
        pool = watch_pool if (watch_pool and RNG.random() < bias) else access_pool or usable
        return RNG.choice(pool or usable)

    for farm_idx, herd in by_farm.items():
        fid = farms[farm_idx - 1].id
        rate = farm_rate[farm_idx]
        n_courses = int(len(herd) * rate * 2.2)
        for _ in range(n_courses):
            animal = RNG.choice(herd)
            drug = pick_drug(farm_idx, animal)
            started_at = NOW - timedelta(days=RNG.uniform(2, 148))
            course_days = RNG.choices([3, 5, 7], weights=[45, 35, 20])[0]
            supervised = RNG.random() < supervision[farm_idx]

            rx_id = None
            if supervised:
                rx = Prescription(
                    vet_id=vet.id, animal_id=animal.id, drug_id=drug.id,
                    diagnosis=RNG.choice(DIAGNOSES),
                    dose_amount=TYPICAL_DOSE[drug.generic_name],
                    route=RNG.choice([Route.im, Route.iv, Route.oral, Route.sc]),
                    frequency_per_day=RNG.choice([1, 2]),
                    duration_days=course_days,
                    issued_at=started_at - timedelta(hours=RNG.uniform(2, 48)),
                )
                db.add(rx)
                db.flush()
                rx_id = rx.id
                stats["prescriptions"] += 1

            record_administration(
                db, animal=animal, drug=drug, started_at=started_at,
                course_days=course_days, dose_amount=TYPICAL_DOSE[drug.generic_name],
                route=rx.route if supervised else Route.im,
                prescription_id=rx_id,
                administered_by_user_id=None,
                batch_number=f"B{RNG.randint(10000, 99999)}",
                cost_inr=RNG.randint(80, 900),
            )
            stats["administrations"] += 1

        # ---- sales history (bulk milk every ~6d on dairy farms) -------------
        # Compliant farmers WITHHOLD withdrawal milk -> most colliding dates are
        # simply skipped. The chronic high-use farm misses ~35% of the time.
        if farm_idx in (1, 3, 5):  # milk-producing
            t = NOW - timedelta(days=140)
            while t < NOW - timedelta(hours=30):
                sloppy = farm_idx == 3 and RNG.random() < 0.35
                if bulk_sale(db, farms[farm_idx - 1], None, SaleProduct.milk,
                             quantity=RNG.uniform(40, 160), occurred_at=t,
                             buyer=("Anand Milk Union", "Karnal Dairy Coop", "Amdanga Milk Soc")[farm_idx % 3],
                             buyer_type=BuyerType.local_dairy,
                             skip_if_violating=not sloppy):
                    stats["sales"] += 1
                t += timedelta(days=RNG.uniform(5, 8))
        elif farm_idx == 2:  # eggs
            t = NOW - timedelta(days=140)
            while t < NOW - timedelta(hours=30):
                if bulk_sale(db, farms[farm_idx - 1], None, SaleProduct.eggs,
                             quantity=RNG.uniform(200, 500), occurred_at=t,
                             buyer="Namakkal Egg Mandi", buyer_type=BuyerType.mandi):
                    stats["sales"] += 1
                t += timedelta(days=RNG.uniform(4, 7))

    db.flush()
    return stats


def bulk_sale(db, farm, animal, product: SaleProduct, *, quantity, occurred_at,
              buyer, buyer_type, skip_if_violating=True) -> SaleEvent | None:
    """Insert a historical sale with engine-computed verdict."""
    from sqlalchemy import select

    if animal is not None:
        windows = enforceable_windows_for_animal(db, animal.id)
    else:
        ids = db.execute(select(Animal.id).where(
            Animal.farm_id == farm.id, Animal.status == "active")).scalars().all()
        from app.services.mrl_engine import enforceable_windows
        windows = enforceable_windows(db, list(ids))

    verdict = evaluate_sale(product, windows, occurred_at)
    if verdict.is_violation and skip_if_violating:
        return None  # farmer withheld this lot -- no sale row at all
    unit = {SaleProduct.milk: "litres", SaleProduct.meat: "kg",
            SaleProduct.eggs: "trays", SaleProduct.live_animal: "birds"}[product]
    sale = SaleEvent(
        farm_id=farm.id,
        animal_id=animal.id if animal else None,
        product_type=product,
        quantity=round(quantity, 1),
        unit=unit,
        buyer_name=buyer,
        buyer_type=buyer_type,
        occurred_at=occurred_at,
        was_under_withdrawal=verdict.was_under_withdrawal,
        is_violation=verdict.is_violation,
        linked_administration_ids=verdict.linked_administration_ids,
        amount_inr=round(quantity * RNG.uniform(25, 60), 0),
    )
    db.add(sale)
    db.flush()
    if verdict.is_violation:
        tissue = {"milk": "milk", "meat": "meat", "eggs": "eggs"}.get(product.value, "product")
        drug_names = ", ".join(sorted({w.drug_name or "?" for w in verdict.violating_windows}))
        alert_service.create_alert(
            db, farm_id=farm.id, animal_id=animal.id if animal else None,
            type_=AlertType.MRL_VIOLATION, severity=AlertSeverity.critical,
            title=f"MRL VIOLATION: {tissue} sold during withdrawal"
                  + (f" ({animal.tag_id})" if animal else ""),
            message=(f"{sale.quantity} {unit} of {tissue} sold on {ist_str(occurred_at)} "
                     f"while within the withdrawal period for {drug_names} "
                     f"({verdict.hours_premature} h premature). Lab testing advised."),
            related_type="sale_event", related_id=sale.id,
        )
    elif verdict.near_miss:
        alert_service.create_alert(
            db, farm_id=farm.id, animal_id=animal.id if animal else None,
            type_=AlertType.NEAR_MISS_SALE, severity=AlertSeverity.info,
            title="Near-miss sale within 24h after clearance",
            message="Sale recorded within 24h after withdrawal clearance — no violation.",
            related_type="sale_event", related_id=sale.id,
        )
    return sale


def scripted_scenarios(db, farms, users, animals, drugs):
    """The five rehearsed stories the golden demo path walks through."""
    vet = vet_user(users)
    by_tag = {a.tag_id: a for a in animals}

    # (a) HARD VIOLATION -- MUR-001 enrofloxacin, milk sold mid-withdrawal ----
    mur = by_tag["MUR-001"]
    started = NOW - timedelta(days=4)           # single-dose course, fully in the past
    admin, rows = record_administration(
        db, animal=mur, drug=drugs["Enrofloxacin"], started_at=started,
        course_days=1, dose_amount=TYPICAL_DOSE["Enrofloxacin"], route=Route.im,
        administered_by_user_id=None, batch_number="B77231", cost_inr=420,
    )
    milk_row = next(r for r in rows if r.tissue.value == "milk")
    sale_time = started + timedelta(hours=18)   # deep inside the 3-day milk WP
    sale = bulk_sale(db, farms[0], mur, SaleProduct.milk, quantity=12.5,
                     occurred_at=sale_time, buyer="Local Society",
                     buyer_type=BuyerType.local_dairy, skip_if_violating=False)
    print(f"[seed] scenario A: violation on {mur.tag_id}, "
          f"{verdict_hours(milk_row.clears_at, sale_time)}h premature")

    # residue test confirming it (regulator lab result)
    db.add(ResidueTest(
        sample_type=SaleProduct.milk, animal_id=mur.id, sale_event_id=sale.id,
        drug_id=drugs["Enrofloxacin"].id, method="HPLC",
        measured_residue_ug_kg=310.0, mrl_reference_ug_kg=100.0,
        result=ResidueResult.fail,
        tested_at=sale_time + timedelta(days=1),
        notes="Enrofloxacin 3x above MRL.",
    ))

    # (b) NEAR MISS -- GIR-002 amoxicillin, milk sold 6h after clearance ------
    gir = by_tag["GIR-002"]
    started_b = NOW - timedelta(days=7)
    _, rows_b = record_administration(
        db, animal=gir, drug=drugs["Amoxicillin"], started_at=started_b,
        course_days=3, dose_amount=TYPICAL_DOSE["Amoxicillin"], route=Route.im,
        administered_by_user_id=None, cost_inr=180,
    )
    milk_b = next(r for r in rows_b if r.tissue.value == "milk")
    bulk_sale(db, farms[0], gir, SaleProduct.milk, quantity=9.0,
              occurred_at=milk_b.clears_at + timedelta(hours=6),
              buyer="Local Society", buyer_type=BuyerType.local_dairy)

    # (c) CHRONIC HIGH USE farm is handled via rates in generate_history (F3).

    # (d) FEVER OUTBREAK buffalo with sensor history ---------------------------
    fever_buf = by_tag["MUR-003"]
    fever_buf.scenario_tag = "fever_outbreak"

    # (e) PROHIBITED DRUG -- colistin on a laying hen --------------------------
    hen = by_tag["VAN-003"]
    col_admin, _ = record_administration(
        db, animal=hen, drug=drugs["Colistin"], started_at=NOW - timedelta(hours=20),
        course_days=3, dose_amount=TYPICAL_DOSE["Colistin"], route=Route.in_water,
        administered_by_user_id=None, cost_inr=90,
        notes="Farmer-reported; no prescription.",
    )
    alert_service.create_alert(
        db, farm_id=farms[1].id, animal_id=hen.id,
        type_=AlertType.PROHIBITED_DRUG_USED, severity=AlertSeverity.critical,
        title=f"PROHIBITED drug used on {hen.tag_id}: Colistin",
        message=("Colistin (Polypeptide, WHO Reserve) is banned in food-producing "
                 "animals but was recorded on laying hen VAN-003. Eggs must not "
                 "enter the market; escalate to regulatory authority."),
        related_type="administration", related_id=col_admin.id,
    )
    db.flush()
    print("[seed] scenarios B-E planted")


def verdict_hours(clears_at, sale_time):
    return round((ensure_aware(clears_at) - ensure_aware(sale_time)).total_seconds() / 3600, 1)


def main() -> None:
    print("[seed] dropping + recreating schema ...")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    db = SessionLocal()
    try:
        drugs = load_formulary(db)
        print(f"[seed] formulary loaded: {len(drugs)} drugs")

        farms, users = create_farms_users(db)
        animals = create_herds(db, farms)
        print(f"[seed] {len(farms)} farms, {len(users)} users, {len(animals)} animals")

        stats = generate_history(db, farms, users, animals, drugs)
        scripted_scenarios(db, farms, users, animals, drugs)

        # ledger entries for every administration + sale (single consistent chain)
        animal_map = {a.id: a for a in animals}
        drug_map = dict(db.query(Drug.id, Drug).all())
        for adm in db.query(Administration).all():
            animal = animal_map[adm.animal_id]
            drug = drug_map[adm.drug_id]
            append_event(
                db, LedgerEventType.administration, adm.id,
                {
                    "animal_tag": animal.tag_id, "qr_code": animal.qr_code,
                    "drug": drug.generic_name, "aware_class": drug.aware_class.value,
                    "dose_mg_kg": adm.dose_amount, "route": adm.route.value,
                    "course_days": adm.course_days,
                    "started_at": adm.started_at.isoformat(),
                    "last_dose_at": adm.last_dose_at.isoformat(),
                    "supervised": adm.prescription_id is not None,
                    "withdrawal_clears_at": {
                        w.tissue.value: w.clears_at.isoformat() for w in adm.withdrawal_periods
                    },
                },
            )
        for sale in db.query(SaleEvent).all():
            animal = animal_map.get(sale.animal_id) if sale.animal_id else None
            append_event(
                db, LedgerEventType.sale_event, sale.id,
                {
                    "sale_event_id": sale.id,
                    "animal_tag": animal.tag_id if animal else "(bulk)",
                    "product_type": sale.product_type.value,
                    "quantity": sale.quantity, "unit": sale.unit,
                    "occurred_at": sale.occurred_at.isoformat() if sale.occurred_at else None,
                    "is_violation": sale.is_violation,
                    "linked_administration_ids": sale.linked_administration_ids,
                },
            )

        # pre-warm IoT readings so charts are full at first login
        active_ids = [a.id for a in animals if a.scenario_tag == "fever_outbreak"][:1]
        dairy_ids = [a.id for a in animals if a.species in (Species.cattle, Species.buffalo)][:6]
        iot_simulator.advance(db, active_ids + dairy_ids, hours_back=72)

        db.commit()

        metrics = train_all(db)

        counts = {
            "administrations": db.query(Administration).count(),
            "prescriptions": db.query(Prescription).count(),
            "sales": db.query(SaleEvent).count(),
            "violations": db.query(SaleEvent).filter_by(is_violation=True).count(),
            "alerts": db.query(Alert).count(),
            "ledger_entries": db.query(TraceLedgerEntry).count(),
            "sensor_readings": db.query(SensorReading).count(),
        }
        ml_metrics = metrics

        print("\n" + "=" * 64)
        print(" PashuSafe demo database seeded")
        print("=" * 64)
        for k, v in counts.items():
            print(f"  {k:>18}: {v}")
        print(f"  {'ml roc_auc':>18}: {ml_metrics}")
        print("-" * 64)
        print(" Demo logins (password: Demo@1234)")
        for _, email, role, _ in USERS:
            print(f"  {role.value:<10} {email}")
        print("=" * 64 + "\n")
    finally:
        db.close()


if __name__ == "__main__":
    main()
