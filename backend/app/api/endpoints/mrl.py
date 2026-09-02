from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel

from app.core.database import get_db
from app.models.mrl import Animal, VeterinaryDrug, TreatmentRecord, AuditLedger, ComplianceStatus, SpeciesType
from app.services.mrl_engine import MRLEngine

router = APIRouter()

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

@router.post("/animals")
async def register_animal(data: AnimalCreate, db: AsyncSession = Depends(get_db)):
    animal = Animal(tag_id=data.tag_id, species=data.species, farmer_id=data.farmer_id)
    db.add(animal)
    await db.commit()
    await db.refresh(animal)
    return animal

@router.post("/drugs")
async def register_drug(data: DrugCreate, db: AsyncSession = Depends(get_db)):
    drug = VeterinaryDrug(**data.model_dump())
    db.add(drug)
    await db.commit()
    await db.refresh(drug)
    return drug

@router.post("/treatments/log")
async def log_treatment(data: TreatmentCreate, db: AsyncSession = Depends(get_db)):
    animal_res = await db.execute(select(Animal).where(Animal.tag_id == data.animal_tag_id))
    animal = animal_res.scalar_one_or_none()
    if not animal:
        raise HTTPException(status_code=404, detail="Animal not found")

    drug_res = await db.execute(select(VeterinaryDrug).where(VeterinaryDrug.id == data.drug_id))
    drug = drug_res.scalar_one_or_none()
    if not drug:
        raise HTTPException(status_code=404, detail="Drug not found")

    safe_date = MRLEngine.compute_withdrawal(data.treatment_end_date, drug, data.commodity)

    treatment = TreatmentRecord(
        animal_id=animal.id,
        drug_id=drug.id,
        rvp_license_number=data.rvp_license_number,
        dosage_administered=data.dosage_administered,
        treatment_start_date=data.treatment_start_date,
        treatment_end_date=data.treatment_end_date,
        computed_safe_date=safe_date
    )
    db.add(treatment)

    animal.status = ComplianceStatus.WITHDRAWAL_ACTIVE
    animal.withdrawal_end_date = safe_date

    last_audit = await db.execute(select(AuditLedger).order_by(desc(AuditLedger.id)).limit(1))
    prev = last_audit.scalar_one_or_none()
    prev_hash = prev.current_hash if prev else "GENESIS_HASH_0000000000000"

    audit_entry = MRLEngine.generate_audit_entry(
        record_id=treatment.id,
        action="TREATMENT_LOGGED",
        previous_hash=prev_hash,
        payload=data.model_dump()
    )
    db.add(audit_entry)

    await db.commit()
    return {"status": "success", "safe_date": safe_date}

@router.get("/procurement/verify/{tag_id}")
async def verify_procurement(tag_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Animal).where(Animal.tag_id == tag_id))
    animal = result.scalar_one_or_none()
    if not animal:
        raise HTTPException(status_code=404, detail="Animal not found")

    return MRLEngine.verify_procurement_safety(animal, date.today())