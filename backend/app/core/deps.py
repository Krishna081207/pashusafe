from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import get_db
from app.models import User
from app.models.enums import Role

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        user_id = int(payload.get("sub", 0))
    except Exception:
        raise credentials_error
    user = db.get(User, user_id)
    if user is None:
        raise credentials_error
    return user


def require_roles(*roles: Role):
    def checker(user: User = Depends(get_current_user)) -> User:
        if roles and user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return user

    return checker


# Convenience bundles matching the plan's role legend.
any_authenticated = require_roles()
farmer_or_admin = require_roles(Role.farmer, Role.admin)
vet_or_admin = require_roles(Role.vet, Role.admin)
regulator_or_admin = require_roles(Role.regulator, Role.admin)
staff = require_roles(Role.farmer, Role.vet, Role.regulator, Role.admin)


def scoped_farm_ids(user: User) -> list[int] | None:
    """Farms this user may read. None => all farms (vet/regulator/admin)."""
    if user.role == Role.farmer:
        return [user.farm_id] if user.farm_id else []
    return None


def ensure_farm_access(user: User, farm_id: int) -> None:
    allowed = scoped_farm_ids(user)
    if allowed is not None and farm_id not in allowed:
        raise HTTPException(status_code=403, detail="Not your farm")
