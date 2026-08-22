from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import Route, Tissue, WithdrawalStatus
from app.utils.timeutil import ensure_aware, utcnow, withdrawal_clears_at


class Prescription(Base):
    __tablename__ = "prescriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    vet_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    animal_id: Mapped[int] = mapped_column(ForeignKey("animals.id"), index=True)
    drug_id: Mapped[int] = mapped_column(ForeignKey("drugs.id"))
    diagnosis: Mapped[str] = mapped_column(String(240))
    dose_amount: Mapped[float] = mapped_column(Float)  # mg/kg
    route: Mapped[Route] = mapped_column(Enum(Route, native_enum=False))
    frequency_per_day: Mapped[int] = mapped_column(Integer, default=1)
    duration_days: Mapped[int] = mapped_column(Integer, default=1)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    administrations: Mapped[list["Administration"]] = relationship(back_populates="prescription")


class Administration(Base):
    """One recorded treatment course. prescription_id NULL => unsupervised/OTC use."""

    __tablename__ = "administrations"
    __table_args__ = (Index("ix_admin_animal_lastdose", "animal_id", "last_dose_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    animal_id: Mapped[int] = mapped_column(ForeignKey("animals.id"), index=True)
    drug_id: Mapped[int] = mapped_column(ForeignKey("drugs.id"), index=True)
    prescription_id: Mapped[int | None] = mapped_column(
        ForeignKey("prescriptions.id"), nullable=True
    )
    administered_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    course_days: Mapped[int] = mapped_column(Integer, default=1)
    last_dose_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    dose_amount: Mapped[float] = mapped_column(Float)  # mg/kg per dose
    route: Mapped[Route] = mapped_column(Enum(Route, native_enum=False), default=Route.im)
    batch_number: Mapped[str | None] = mapped_column(String(80), nullable=True)
    cost_inr: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    drug: Mapped["Drug"] = relationship()  # noqa: F821
    animal: Mapped["Animal"] = relationship()  # noqa: F821
    prescription: Mapped["Prescription | None"] = relationship(back_populates="administrations")
    withdrawal_periods: Mapped[list["WithdrawalPeriod"]] = relationship(
        back_populates="administration", cascade="all, delete-orphan"
    )

    def compute_last_dose(self) -> None:
        from datetime import timedelta

        self.last_dose_at = self.started_at + timedelta(days=max(self.course_days - 1, 0))


class WithdrawalPeriod(Base):
    """Materialized compliance row -- one per applicable tissue per administration.

    All countdown / status queries read this table; the engine never recomputes.
    """

    __tablename__ = "withdrawal_periods"

    id: Mapped[int] = mapped_column(primary_key=True)
    administration_id: Mapped[int] = mapped_column(
        ForeignKey("administrations.id"), unique=False, index=True
    )
    tissue: Mapped[Tissue] = mapped_column(Enum(Tissue, native_enum=False))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    clears_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[WithdrawalStatus] = mapped_column(
        Enum(WithdrawalStatus, native_enum=False), default=WithdrawalStatus.active
    )

    administration: Mapped["Administration"] = relationship(back_populates="withdrawal_periods")

    @staticmethod
    def build(administration: "Administration", tissue: Tissue, wp_days: float) -> "WithdrawalPeriod":
        """Unsafe interval = [first dose ... last dose + labelled WP]."""
        return WithdrawalPeriod(
            tissue=tissue,
            starts_at=administration.started_at,
            clears_at=withdrawal_clears_at(administration.last_dose_at, wp_days),
            status=WithdrawalStatus.active,
        )

    def is_active_at(self, when: datetime) -> bool:
        w = ensure_aware(when)
        return (
            ensure_aware(self.starts_at) <= w < ensure_aware(self.clears_at)
            and self.status == WithdrawalStatus.active
        )
