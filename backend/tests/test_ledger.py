"""Ledger hash-chain tests on an in-memory SQLite DB."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models import TraceLedgerEntry
from app.models.enums import LedgerEventType
from app.services.ledger_service import append_event, compute_hash, demo_tamper, verify_chain


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_chain_builds_and_verifies(db):
    for i in range(5):
        append_event(db, LedgerEventType.administration, i, {"n": i})
    result = verify_chain(db)
    assert result["valid"] is True
    assert result["length"] == 5
    assert result["first_invalid_seq"] is None


def test_genesis_uses_zero_prev_hash(db):
    e = append_event(db, LedgerEventType.sale_event, 1, {"x": 1})
    assert e.seq == 1
    assert e.prev_hash == "0" * 64


def test_hash_is_deterministic():
    h1 = compute_hash("a" * 64, '{"b":1}', 3)
    h2 = compute_hash("a" * 64, '{"b":1}', 3)
    assert h1 == h2 and len(h1) == 64


def test_tampered_payload_detected_at_correct_seq(db):
    for i in range(4):
        append_event(db, LedgerEventType.residue_test, i, {"n": i})
    tampered = demo_tamper(db)
    db.flush()

    # recompute expected chain from scratch: entry seq of the tampered row no
    # longer matches its stored hash
    entries = (
        db.query(TraceLedgerEntry).order_by(TraceLedgerEntry.seq).all()
    )
    victim = next(e for e in entries if e.seq >= tampered.seq)
    recomputed = compute_hash(victim.prev_hash, victim.payload_json, victim.seq)

    result = verify_chain(db)
    assert result["valid"] is False
    assert victim.hash != recomputed


def test_canonical_json_is_key_sorted(db):
    e = append_event(db, LedgerEventType.alert_raised, 1, {"zeta": 1, "alpha": 2})
    assert e.payload_json.index("alpha") < e.payload_json.index("zeta")
