#!/usr/bin/env python3
"""Reproduce everything the animal-detail page calls, printing tracebacks.

    ./.venv/bin/python scripts/debug_detail.py
"""

import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal  # noqa: E402
from app.models import Animal, User  # noqa: E402
from app.services import iot_simulator  # noqa: E402
from app.services.ml import features as feat  # noqa: E402
from app.services.ml import serve  # noqa: E402
from app.services.mrl_engine import animal_compliance  # noqa: E402


def check(label, fn):
    try:
        result = fn()
        n = None
        if isinstance(result, list):
            n = f"{len(result)} rows"
        elif isinstance(result, dict):
            n = f"keys={sorted(result.keys())[:6]}..."
        print(f"[OK]   {label}  ({n})")
        return result
    except Exception:
        print(f"[FAIL] {label}")
        traceback.print_exc()
        print("-" * 70)
        return None


def main():
    db = SessionLocal()
    try:
        farmer = db.query(User).filter_by(email="ravi@demo.in").first()
        animal = db.query(Animal).filter_by(farm_id=farmer.farm_id).first()
        print(f"context: farmer={farmer.email} farm={farmer.farm_id} "
              f"animal={animal.tag_id} id={animal.id}\n")

        check("animal_compliance (dossier core)", lambda: animal_compliance(db, animal))
        check("ml mrl_features", lambda: feat.mrl_features(db, animal))
        check("ml outbreak_features", lambda: feat.outbreak_features(db, animal))

        def _pred():
            mf = feat.mrl_features(db, animal)
            of = feat.outbreak_features(db, animal)
            return {
                "mrl": serve.predict_mrl(mf),
                "outbreak": serve.predict_outbreak(of) if of else None,
            }
        check("ml predictions (serve)", _pred)

        def _iot():
            iot_simulator.advance(db, [animal.id], hours_back=48)
            return iot_simulator.readings_for(db, animal.id, hours=48)
        readings = check("iot advance + readings", _iot)

        if readings:
            print(f"       sample reading: {readings[-1]}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
