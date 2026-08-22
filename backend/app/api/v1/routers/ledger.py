from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models import User
from app.services import ledger_service

router = APIRouter(prefix="/ledger", tags=["ledger"])


@router.get("/events")
def events(
    limit: int = 50,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles()),
):
    rows = ledger_service.recent_entries(db, limit=min(limit, 200))
    return [
        {
            "seq": e.seq,
            "event_type": e.event_type.value,
            "entity_id": e.entity_id,
            "payload": e.payload_json,
            "prev_hash": e.prev_hash[:16] + "...",
            "hash": e.hash,
            "actor_user_id": e.actor_user_id,
            "recorded_at": e.recorded_at.isoformat() if e.recorded_at else None,
        }
        for e in rows
    ]


@router.get("/verify")
def verify(db: Session = Depends(get_db)):
    """Replay the whole chain -- public so judges/buyers can audit live."""
    return ledger_service.verify_chain(db)


@router.post("/demo-tamper")
def demo_tamper(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    """DEV ONLY: corrupt one payload so /verify flips red during the demo."""
    s = get_settings()
    if s.environment != "development":
        from fastapi import HTTPException

        raise HTTPException(403, "Only available in development environment")
    entry = ledger_service.demo_tamper(db)
    db.commit()
    if entry is None:
        return {"ok": False, "message": "Ledger is empty"}
    return {"ok": True, "tampered_seq": entry.seq}
