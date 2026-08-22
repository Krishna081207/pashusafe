from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import BuyerType, ResidueResult, SaleProduct
from app.utils.timeutil import utcnow


class SaleEvent(Base):
    """Milk/meat/eggs/live-animal sale. Compliance verdict is frozen at insert
    time as evidence (was_under_withdrawal / is_violation)."""

    __tablename__ = "sale_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    farm_id: Mapped[int] = mapped_column(ForeignKey("farms.id"), index=True)
    animal_id: Mapped[int | None] = mapped_column(ForeignKey("animals.id"), nullable=True)
    product_type: Mapped[SaleProduct] = mapped_column(Enum(SaleProduct, native_enum=False))
    quantity: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(20), default="litres")
    buyer_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    buyer_type: Mapped[BuyerType | None] = mapped_column(
        Enum(BuyerType, native_enum=False), nullable=True
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    was_under_withdrawal: Mapped[bool] = mapped_column(Boolean, default=False)
    is_violation: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    linked_administration_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    amount_inr: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    animal: Mapped["Animal | None"] = relationship()  # noqa: F821


class ResidueTest(Base):
    __tablename__ = "residue_tests"

    id: Mapped[int] = mapped_column(primary_key=True)
    sample_type: Mapped[SaleProduct] = mapped_column(Enum(SaleProduct, native_enum=False))
    animal_id: Mapped[int | None] = mapped_column(ForeignKey("animals.id"), nullable=True)
    sale_event_id: Mapped[int | None] = mapped_column(
        ForeignKey("sale_events.id"), nullable=True
    )
    drug_id: Mapped[int] = mapped_column(ForeignKey("drugs.id"))
    lab_name: Mapped[str] = mapped_column(String(160), default="State Vet Lab")
    method: Mapped[str] = mapped_column(String(40), default="SNAP")  # SNAP/ELISA/HPLC
    measured_residue_ug_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    mrl_reference_ug_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    result: Mapped[ResidueResult] = mapped_column(
        Enum(ResidueResult, native_enum=False), default=ResidueResult.pending
    )
    tested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    drug: Mapped["Drug"] = relationship()  # noqa: F821
    animal: Mapped["Animal | None"] = relationship()  # noqa: F821
