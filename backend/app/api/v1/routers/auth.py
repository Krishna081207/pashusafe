from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models import Farm, User
from app.models.enums import Role
from app.schemas import FarmerRegisterIn, StaffRegisterIn, TokenOut, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_response(user: User) -> TokenOut:
    return TokenOut(
        access_token=create_access_token(user.id, user.role.value, user.farm_id),
        role=user.role,
        farm_id=user.farm_id,
        full_name=user.full_name,
    )


@router.post("/register", response_model=TokenOut)
def register_farmer(payload: FarmerRegisterIn, db: Session = Depends(get_db)):
    """Self-service registration: creates the farmer account AND their farm."""
    exists = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=409, detail="Email already registered")
    farm = Farm(
        name=payload.farm_name,
        village=payload.village,
        district=payload.district,
        state=payload.state,
        pincode=payload.pincode,
    )
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
