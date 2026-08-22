from datetime import datetime

from sqlalchemy import CHAR, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import LedgerEventType
from app.utils.timeutil import utcnow

GENESIS_PREV_HASH = "0" * 64


class TraceLedgerEntry(Base):
    """Append-only hash chain: hash_n = sha256(prev_hash + canonical_payload + seq)."""

    __tablename__ = "trace_ledger"

    seq: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    event_type: Mapped[LedgerEventType] = mapped_column(Enum(LedgerEventType, native_enum=False))
    entity_id: Mapped[int] = mapped_column(Integer, index=True)
    payload_json: Mapped[str] = mapped_column(Text)
    prev_hash: Mapped[str] = mapped_column(CHAR(64))
    hash: Mapped[str] = mapped_column(CHAR(64), index=True)
    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
