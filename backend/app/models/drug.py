from sqlalchemy import Boolean, Enum, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import AWaReClass, Species


class Drug(Base):
    __tablename__ = "drugs"

    id: Mapped[int] = mapped_column(primary_key=True)
    generic_name: Mapped[str] = mapped_column(String(120), unique=True)
    active_ingredient: Mapped[str | None] = mapped_column(String(160), nullable=True)
    drug_class: Mapped[str] = mapped_column(String(80))
    aware_class: Mapped[AWaReClass] = mapped_column(Enum(AWaReClass, native_enum=False))
    prohibited_in_food_animals: Mapped[bool] = mapped_column(Boolean, default=False)
    prohibited_in_lactating_animals: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    rules: Mapped[list["DrugSpeciesRule"]] = relationship(back_populates="drug")


class DrugSpeciesRule(Base):
    """Withdrawal period x MRL matrix for one (drug, species) pair.

    NULL withdrawal_*_days means that tissue is not regulated for the pair.
    Values are approximate Codex Alimentarius / FSSAI figures for demo purposes.
    """

    __tablename__ = "drug_species_rules"
    __table_args__ = (UniqueConstraint("drug_id", "species", name="uq_drug_species"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    drug_id: Mapped[int] = mapped_column(ForeignKey("drugs.id"), index=True)
    species: Mapped[Species] = mapped_column(Enum(Species, native_enum=False))
    route_default: Mapped[str | None] = mapped_column(String(40), nullable=True)
    withdrawal_milk_days: Mapped[float | None] = mapped_column(Float, nullable=True)
    withdrawal_meat_days: Mapped[float | None] = mapped_column(Float, nullable=True)
    withdrawal_eggs_days: Mapped[float | None] = mapped_column(Float, nullable=True)
    mrl_milk_ug_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    mrl_meat_ug_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    mrl_eggs_ug_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(160), default="Codex/FSSAI (approx., demo)")

    drug: Mapped["Drug"] = relationship(back_populates="rules")
