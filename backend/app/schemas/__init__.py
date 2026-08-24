from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.enums import (
    BuyerType,
    PreferredSlot,
    ProductionStatus,
    ResidueResult,
    Role,
    Route,
    SaleProduct,
    Sex,
    Species,
    VisitStatus,
)
from app.utils.timeutil import ist_date, utcnow


# ---- auth ----
class LivestockProfileIn(BaseModel):
    """Livestock questions answered during farmer registration."""

    species_owned: list[Species] = []
    species_counts: dict[Species, int] | None = Field(
        default=None, description="head count per species, e.g. {cattle: 4}"
    )
    herd_size_total: int | None = Field(default=None, ge=1, le=100_000)
    main_breeds: str | None = Field(default=None, max_length=240)


class InstallVisitRequestIn(BaseModel):
    """Preferred slot for the IoT sensor installation visit."""

    preferred_date: date
    preferred_slot: PreferredSlot = PreferredSlot.morning
    notes: str | None = Field(default=None, max_length=300)

    @field_validator("preferred_date")
    @classmethod
    def _not_past(cls, v: date) -> date:
        if v < ist_date(utcnow()):
            raise ValueError("preferred_date must be today or later")
        return v


class FarmerRegisterIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str | None = None
    password: str = Field(min_length=8)
    farm_name: str = Field(min_length=2, max_length=120)
    village: str | None = None
    district: str | None = None
    state: str | None = None
    pincode: str | None = None
    # optional extras -- legacy payloads without them still validate
    profile: LivestockProfileIn | None = None
    install_visit: InstallVisitRequestIn | None = None


class StaffRegisterIn(BaseModel):
    """Admin-only creation of vet/regulator/admin accounts."""

    full_name: str
    email: EmailStr
    password: str = Field(min_length=8)
    role: Role


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Role
    farm_id: int | None = None
    full_name: str


class UserOut(BaseModel):
    id: int
    full_name: str
    email: str
    role: Role
    farm_id: int | None
    phone: str | None = None


class InstallVisitUpdateIn(BaseModel):
    """Admin actions on an installation visit (partial update)."""

    status: VisitStatus | None = None
    scheduled_at: datetime | None = None
    official_name: str | None = Field(default=None, max_length=120)
    official_phone: str | None = Field(default=None, max_length=20)
    cancel_reason: str | None = Field(default=None, max_length=240)


# ---- farm ----
class FarmOut(BaseModel):
    id: int
    name: str
    village: str | None
    district: str | None
    state: str | None
    pincode: str | None


# ---- animal ----
class AnimalIn(BaseModel):
    tag_id: str = Field(min_length=2, max_length=32)
    species: Species
    breed: str | None = None
    sex: Sex = Sex.female
    birth_date: date | None = None
    production_status: ProductionStatus = ProductionStatus.lactating
    weight_kg: float | None = None
    scenario_tag: str | None = None


class AnimalUpdate(BaseModel):
    production_status: ProductionStatus | None = None
    weight_kg: float | None = None
    status: str | None = None
    breed: str | None = None


# ---- drugs ----
class DrugRuleOut(BaseModel):
    id: int
    drug_id: int
    species: Species
    withdrawal_milk_days: float | None
    withdrawal_meat_days: float | None
    withdrawal_eggs_days: float | None
    mrl_milk_ug_kg: float | None
    mrl_meat_ug_kg: float | None
    mrl_eggs_ug_kg: float | None
    source: str


class DrugOut(BaseModel):
    id: int
    generic_name: str
    active_ingredient: str | None
    drug_class: str
    aware_class: str
    prohibited_in_food_animals: bool
    prohibited_in_lactating_animals: bool
    notes: str | None
    rules: list[DrugRuleOut] = []


# ---- prescriptions / administrations ----
class PrescriptionIn(BaseModel):
    animal_id: int
    drug_id: int
    diagnosis: str
    dose_amount: float = Field(gt=0, description="mg/kg")
    route: Route
    frequency_per_day: int = 1
    duration_days: int = Field(default=1, ge=1)
    notes: str | None = None


class AdministrationIn(BaseModel):
    animal_id: int
    drug_id: int
    prescription_id: int | None = None
    started_at: datetime | None = Field(
        default=None, description="Defaults to now (UTC accepted; ISO with offset)"
    )
    course_days: int = Field(default=1, ge=1, le=60)
    dose_amount: float = Field(gt=0, description="mg/kg per dose")
    route: Route = Route.im
    batch_number: str | None = None
    cost_inr: float | None = None
    notes: str | None = None


# ---- sales / residue tests ----
class SaleEventIn(BaseModel):
    product_type: SaleProduct
    quantity: float = Field(gt=0)
    unit: str | None = None
    animal_id: int | None = None
    buyer_name: str | None = None
    buyer_type: BuyerType | None = None
    occurred_at: datetime | None = None
    amount_inr: float | None = None
    notes: str | None = None
    acknowledge_warning: bool = Field(
        default=False,
        description="Must be true when the system flags an active withdrawal",
    )


class ResidueTestIn(BaseModel):
    sample_type: SaleProduct
    drug_id: int
    animal_id: int | None = None
    sale_event_id: int | None = None
    method: str = "SNAP"
    measured_residue_ug_kg: float | None = None
    result: ResidueResult
    notes: str | None = None
