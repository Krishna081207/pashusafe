from datetime import date, datetime
import uuid

from sqlalchemy import Date, DateTime, Enum, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import AnimalStatus, ProductionStatus, Sex, Species
from app.utils.timeutil import utcnow


def new_qr_code() -> str:
    return uuid.uuid4().hex


class Animal(Base):
    __tablename__ = "animals"
    __table_args__ = (UniqueConstraint("farm_id", "tag_id", name="uq_farm_tag"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    farm_id: Mapped[int] = mapped_column(ForeignKey("farms.id"), index=True)
    tag_id: Mapped[str] = mapped_column(String(32))  # human-readable e.g. GIR-0042
    species: Mapped[Species] = mapped_column(Enum(Species, native_enum=False))
    breed: Mapped[str | None] = mapped_column(String(80), nullable=True)
    sex: Mapped[Sex] = mapped_column(Enum(Sex, native_enum=False), default=Sex.female)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    production_status: Mapped[ProductionStatus] = mapped_column(
        Enum(ProductionStatus, native_enum=False), default=ProductionStatus.lactating
    )
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[AnimalStatus] = mapped_column(
        Enum(AnimalStatus, native_enum=False), default=AnimalStatus.active
    )
    qr_code: Mapped[str] = mapped_column(String(64), unique=True, default=new_qr_code)
    # demo scenario hook consumed by the IoT simulator + ML demo:
    scenario_tag: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    farm: Mapped["Farm"] = relationship(back_populates="animals")  # noqa: F821
