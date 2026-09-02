from datetime import date
from pydantic import BaseModel
from app.models.livestock import SpeciesType, ComplianceStatus

class AnimalCreate(BaseModel):
    tag_id: str
    species: SpeciesType
    farmer_id: str

class DrugCreate(BaseModel):
    brand_name: str
    active_ingredient: str
    who_classification: str
    mrl_limit_ppm: float
    milk_withdrawal_days: int
    meat_withdrawal_days: int

class TreatmentCreate(BaseModel):
    animal_tag_id: str
    drug_id: str
    rvp_license_number: str
    dosage_administered: str
    treatment_start_date: date
    treatment_end_date: date
    commodity: str = "milk"