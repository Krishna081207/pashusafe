import enum
import uuid
from datetime import datetime, date
from sqlalchemy import String, Integer, Float, Date, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class SpeciesType(str, enum.Enum):
    BOVINE = "BOVINE"      # Cattle / Buffalo
    OVINE = "OVINE"        # Sheep
    CAPRINE = "CAPRINE"    # Goat
    POULTRY = "POULTRY"

class ComplianceStatus(str, enum.Enum):
    SAFE = "SAFE"
    WITHDRAWAL_ACTIVE = "WITHDRAWAL_ACTIVE"
    VIOLATION_FLAGGED = "VIOLATION_FLAGGED"

class Animal(Base):
    __tablename__ = "animals"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tag_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    species: Mapped[SpeciesType] = mapped_column(Enum(SpeciesType), nullable=False)
    farmer_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[ComplianceStatus] = mapped_column(
        Enum(ComplianceStatus), default=ComplianceStatus.SAFE
    )
    withdrawal_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    treatments: Mapped[list["TreatmentRecord"]] = relationship(back_populates="animal")

class VeterinaryDrug(Base):
    __tablename__ = "veterinary_drugs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    brand_name: Mapped[str] = mapped_column(String(128), index=True)
    active_ingredient: Mapped[str] = mapped_column(String(128), index=True)
    who_classification: Mapped[str] = mapped_column(String(64))  # CIA / HPCI / Standard
    mrl_limit_ppm: Mapped[float] = mapped_column(Float, nullable=False)
    milk_withdrawal_days: Mapped[int] = mapped_column(Integer, default=0)
    meat_withdrawal_days: Mapped[int] = mapped_column(Integer, default=0)

class TreatmentRecord(Base):
    __tablename__ = "treatment_records"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    animal_id: Mapped[str] = mapped_column(ForeignKey("animals.id"), nullable=False)
    drug_id: Mapped[str] = mapped_column(ForeignKey("veterinary_drugs.id"), nullable=False)
    rvp_license_number: Mapped[str] = mapped_column(String(64), nullable=False)
    dosage_administered: Mapped[str] = mapped_column(String(64), nullable=False)
    treatment_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    treatment_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    computed_safe_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    animal: Mapped["Animal"] = relationship(back_populates="treatments")
    drug: Mapped["VeterinaryDrug"] = relationship()

class AuditLedger(Base):
    __tablename__ = "audit_ledger"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    record_id: Mapped[str] = mapped_column(String, nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    previous_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    current_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)