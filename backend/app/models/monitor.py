from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import AlertAudience, AlertSeverity, AlertType
from app.utils.timeutil import utcnow


class SensorReading(Base):
    __tablename__ = "sensor_readings"
    __table_args__ = (
        UniqueConstraint("animal_id", "recorded_at", name="uq_sensor_animal_time"),
        Index("ix_sensor_animal_time", "animal_id", "recorded_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    animal_id: Mapped[int] = mapped_column(ForeignKey("animals.id"), index=True)
    device_id: Mapped[str] = mapped_column(String(40))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    body_temp_c: Mapped[float] = mapped_column(Float)
    activity_index: Mapped[float] = mapped_column(Float)  # 0-100
    rumination_min: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (Index("ix_alerts_farm_unresolved", "farm_id", "resolved_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    farm_id: Mapped[int] = mapped_column(ForeignKey("farms.id"), index=True)
    animal_id: Mapped[int | None] = mapped_column(ForeignKey("animals.id"), nullable=True)
    type: Mapped[AlertType] = mapped_column(Enum(AlertType, native_enum=False))
    severity: Mapped[AlertSeverity] = mapped_column(Enum(AlertSeverity, native_enum=False))
    audience: Mapped[AlertAudience] = mapped_column(
        Enum(AlertAudience, native_enum=False),
        default=AlertAudience.all,
        server_default="all",
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200))
    message: Mapped[str] = mapped_column(Text)
    related_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    related_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
