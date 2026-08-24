from datetime import UTC, datetime, timedelta

import hashlib
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models import Animal, Farm, SensorInstallVisit, User
from app.models.enums import LedgerEventType, ProductionStatus, Role, Sex, Species
from app.schemas import FarmerRegisterIn, LivestockProfileIn, StaffRegisterIn, TokenOut, UserOut
from app.services import ledger_service

router = APIRouter(prefix="/auth", tags=["auth"])

# --- starter herd: turn the wizard's livestock answers into real records ----
_TAG_PREFIX = {"cattle": "CAT", "buffalo": "BUF", "goat": "GOA",
               "sheep": "SHE", "pig": "PIG", "poultry": "POU"}
_WEIGHT_KG = {"cattle": (280, 480), "buffalo": (350, 550), "goat": (28, 55),
              "sheep": (30, 60), "pig": (60, 110), "poultry": (1.8, 2.8)}
_MAX_PER_SPECIES = 20
_MAX_TOTAL = 40


def _hash_uniform(seed: str) -> float:
    digest = hashlib.sha256(seed.encode()).digest()
    return int.from_bytes(digest[:8], "big") / 2**64


def _create_starter_herd(db: Session, farm: Farm, user: User, profile: LivestockProfileIn) -> int:
    """Populate the farm with animals matching the registration answers so the
    new farmer's registry / dashboards / tracking map are alive immediately."""
    breeds = [b.strip() for b in (profile.main_breeds or "").split(",") if b.strip()]
    counts = dict(profile.species_counts) if profile.species_counts else {}
    if not counts:
        # no counts given -- a small token herd per declared species (demo-grade)
        counts = {s.value: 2 for s in profile.species_owned}
    if not counts:
        return 0

    total = min(sum(counts.values()), _MAX_TOTAL)
    created = 0
    for species_name, want in counts.items():
        try:
            species = Species(species_name)
        except ValueError:
            continue
        n = max(0, min(want, _MAX_PER_SPECIES, total - created))
        prefix = _TAG_PREFIX[species.value]
        for i in range(1, n + 1):
            seed = f"{farm.id}-{prefix}-{i}"
            lo, hi = _WEIGHT_KG[species.value]
            age_years = 2 + 4 * _hash_uniform(f"{seed}-age")
            animal = Animal(
                farm_id=farm.id,
                tag_id=f"{prefix}-{i:03d}",
                species=species,
                breed=breeds[(created + i - 1) % len(breeds)] if breeds else None,
                sex=Sex.female,
                birth_date=(datetime.now(UTC) - timedelta(days=int(age_years * 365))).date(),
                production_status=(
                    ProductionStatus.laying
                    if species == Species.poultry
                    else ProductionStatus.lactating
                ),
                weight_kg=round(lo + (hi - lo) * _hash_uniform(f"{seed}-wt"), 1),
            )
            db.add(animal)
            db.flush()
            ledger_service.append_event(
                db,
                LedgerEventType.animal_registered,
                animal.id,
                {
                    "tag_id": animal.tag_id,
                    "species": animal.species.value,
                    "breed": animal.breed,
                    "farm_id": animal.farm_id,
                },
                actor_user_id=user.id,
            )
            created += 1
        if created >= total:
            break
    return created


def _token_response(user: User) -> TokenOut:
    return TokenOut(
        access_token=create_access_token(user.id, user.role.value, user.farm_id),
        role=user.role,
        farm_id=user.farm_id,
        full_name=user.full_name,
    )


@router.post("/register", response_model=TokenOut)
def register_farmer(payload: FarmerRegisterIn, db: Session = Depends(get_db)):
    """Self-service registration: creates the farmer account AND their farm.

    Optionally captures a livestock profile and an IoT sensor installation
    visit request in the same call.
    """
    exists = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=409, detail="Email already registered")
    profile = payload.profile
    counts = profile.species_counts if profile else None
    # NB: omit unset JSON fields entirely -- assigning raw None would persist
    # the literal JSON string 'null' instead of SQL NULL.
    farm_kwargs: dict = {
        "name": payload.farm_name,
        "village": payload.village,
        "district": payload.district,
        "state": payload.state,
        "pincode": payload.pincode,
    }
    if profile:
        if profile.species_owned:
            farm_kwargs["species_owned"] = [s.value for s in profile.species_owned]
        if counts:
            farm_kwargs["species_counts"] = {k.value: v for k, v in counts.items()}
            farm_kwargs["herd_size_total"] = (
                profile.herd_size_total or sum(counts.values())
            )
        elif profile.herd_size_total:
            farm_kwargs["herd_size_total"] = profile.herd_size_total
        if profile.main_breeds:
            farm_kwargs["main_breeds"] = profile.main_breeds
    farm = Farm(**farm_kwargs)
    db.add(farm)
    db.flush()
    user = User(
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        role=Role.farmer,
        farm_id=farm.id,
    )
    db.add(user)
    db.flush()
    if payload.install_visit:
        db.add(
            SensorInstallVisit(
                farm_id=farm.id,
                requested_by_user_id=user.id,
                preferred_date=payload.install_visit.preferred_date,
                preferred_slot=payload.install_visit.preferred_slot,
                notes=payload.install_visit.notes,
            )
        )
    if payload.profile:
        _create_starter_herd(db, farm, user, payload.profile)
    db.commit()
    db.refresh(user)
    return _token_response(user)


@router.post("/staff", response_model=UserOut)
def register_staff(
    payload: StaffRegisterIn,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(Role.admin)),
):
    """Admin creates vet/regulator/admin accounts."""
    exists = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(
        full_name=payload.full_name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenOut)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.email == form.username)).scalar_one_or_none()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    return _token_response(user)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
