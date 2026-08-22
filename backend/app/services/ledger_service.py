"""Blockchain-lite traceability: append-only sha256 hash chain.

    hash_n = sha256( prev_hash + canonical_payload_json + str(seq) )

Every supply-chain-relevant domain write appends an entry inside the SAME
transaction, so provenance is atomic with the fact. `verify_chain()` replays
the whole chain and reports the first tampered seq.
"""

import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import TraceLedgerEntry
from app.models.enums import LedgerEventType


def canonical(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def compute_hash(prev_hash: str, payload_json: str, seq: int) -> str:
    return hashlib.sha256(f"{prev_hash}{payload_json}{seq}".encode()).hexdigest()


def append_event(
    db: Session,
    event_type: LedgerEventType,
    entity_id: int,
    payload: dict,
    actor_user_id: int | None = None,
) -> TraceLedgerEntry:
    prev = db.execute(
        select(TraceLedgerEntry).order_by(TraceLedgerEntry.seq.desc()).limit(1)
    ).scalar_one_or_none()
    entry = TraceLedgerEntry(
        event_type=event_type,
        entity_id=entity_id,
        payload_json=canonical(payload),
        prev_hash=prev.hash if prev else "0" * 64,
        actor_user_id=actor_user_id,
    )
    entry.seq = (prev.seq + 1) if prev else 1
    entry.hash = compute_hash(entry.prev_hash, entry.payload_json, entry.seq)
    db.add(entry)
    db.flush()
    return entry


def verify_chain(db: Session) -> dict:
    entries = db.execute(
        select(TraceLedgerEntry).order_by(TraceLedgerEntry.seq.asc())
    ).scalars().all()

    first_invalid: int | None = None
    expected_prev = "0" * 64
    for e in entries:
        if first_invalid is None:
            recomputed = compute_hash(expected_prev, e.payload_json, e.seq)
            if e.prev_hash != expected_prev or e.hash != recomputed:
                first_invalid = e.seq
        expected_prev = e.hash  # chain forward regardless, so length stays accurate

    return {
        "valid": first_invalid is None,
        "length": len(entries),
        "first_invalid_seq": first_invalid,
        "algorithm": "sha256(prev_hash + canonical_payload + seq)",
    }


def demo_tamper(db: Session) -> TraceLedgerEntry | None:
    """Flip one payload value in the oldest administration entry (dev/demo only).
    Falls back to the oldest entry of any type when no administration exists."""
    entry = db.execute(
        select(TraceLedgerEntry)
        .where(TraceLedgerEntry.event_type == LedgerEventType.administration)
        .order_by(TraceLedgerEntry.seq.asc())
        .limit(1)
    ).scalar_one_or_none()
    if entry is None:
        entry = db.execute(
            select(TraceLedgerEntry).order_by(TraceLedgerEntry.seq.asc()).limit(1)
        ).scalar_one_or_none()
    if entry is None:
        return None
    payload = json.loads(entry.payload_json)
    if "dose_amount" in payload:
        payload["dose_amount"] = round(float(payload["dose_amount"]) + 111.0, 3)
    elif payload:
        key = sorted(payload.keys())[0]
        payload[key] = f"TAMPERED-{payload[key]}"
    entry.payload_json = canonical(payload)
    db.flush()
    return entry


def recent_entries(db: Session, limit: int = 50) -> list[TraceLedgerEntry]:
    return list(
        db.execute(
            select(TraceLedgerEntry)
            .order_by(TraceLedgerEntry.seq.desc())
            .limit(limit)
        ).scalars().all()
    )
