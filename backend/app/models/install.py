from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import PreferredSlot, VisitStatus
from app.utils.timeutil import utcnow


class SensorInstallVisit(Base):
    """IoT sensor installation visit: farmer requests a slot, admin confirms."""

    __tablename__ = "sensor_install_visits"

    id: Mapped[int] = mapped_column(primary_key=True)
    farm_id: Mapped[int] = mapped_column(ForeignKey("farms.id"), index=True)
    requested_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[VisitStatus] = mapped_column(
        Enum(VisitStatus, native_enum=False), default=VisitStatus.requested
    )
    preferred_date: Mapped[date] = mapped_column(Date)
    preferred_slot: Mapped[PreferredSlot] = mapped_column(
        Enum(PreferredSlot, native_enum=False), default=PreferredSlot.morning
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # final confirmed slot + installation official (set by admin)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    official_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    official_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(String(240), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    farm: Mapped["Farm"] = relationship()  # noqa: F821
