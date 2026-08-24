from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.utils.timeutil import utcnow


class AnimalPosition(Base):
    """One GPS fix from a (simulated) collar. Template: SensorReading."""

    __tablename__ = "animal_positions"
    __table_args__ = (
        UniqueConstraint("animal_id", "recorded_at", name="uq_pos_animal_time"),
        Index("ix_pos_animal_time", "animal_id", "recorded_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    animal_id: Mapped[int] = mapped_column(ForeignKey("animals.id"), index=True)
    device_id: Mapped[str] = mapped_column(String(40))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    speed_kmh: Mapped[float] = mapped_column(Float, default=0.0)
    distance_from_center_m: Mapped[float] = mapped_column(Float)  # denormalised for breach checks
    inside_geofence: Mapped[bool] = mapped_column(Boolean, default=True)


class Geofence(Base):
    """Circular farm boundary -- one per farm."""

    __tablename__ = "geofences"

    id: Mapped[int] = mapped_column(primary_key=True)
    farm_id: Mapped[int] = mapped_column(ForeignKey("farms.id"), unique=True, index=True)
    center_lat: Mapped[float] = mapped_column(Float)
    center_lng: Mapped[float] = mapped_column(Float)
    radius_m: Mapped[float] = mapped_column(Float, default=300.0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
