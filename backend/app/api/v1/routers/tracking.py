"""Farmer-only live animal tracking: simulated GPS feed + circular geofence.

The geofence is one circle per farm. Breach alerts are raised with
`audience=farmer`, so vets/regulators/admins never see them.
"""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import ensure_farm_access, require_roles
from app.db.session import get_db
from app.models import Animal, AnimalPosition, Farm, Geofence, User
from app.models.enums import Role
from app.services import gps_simulator
from app.services.geo import haversine_m
from app.utils.timeutil import ensure_aware, ist_str, utcnow

router = APIRouter(prefix="/tracking", tags=["tracking"])

DEFAULT_CENTER = (22.57, 72.95)  # Anand, Gujarat -- matches seed farms


class GeofenceIn(BaseModel):
    center_lat: float = Field(ge=-90, le=90)
    center_lng: float = Field(ge=-180, le=180)
    radius_m: float = Field(gt=19, le=10_000)
    enabled: bool = True


def _get_or_create_fence(db: Session, farm: Farm) -> Geofence:
    fence = db.execute(
        select(Geofence).where(Geofence.farm_id == farm.id)
    ).scalar_one_or_none()
    if fence is None:
        fence = Geofence(
            farm_id=farm.id,
            center_lat=farm.latitude if farm.latitude is not None else DEFAULT_CENTER[0],
            center_lng=farm.longitude if farm.longitude is not None else DEFAULT_CENTER[1],
        )
        db.add(fence)
        db.flush()
    return fence


def _serialize_fence(fence: Geofence) -> dict:
    return {
        "center_lat": fence.center_lat,
        "center_lng": fence.center_lng,
        "radius_m": fence.radius_m,
        "enabled": fence.enabled,
        "updated_at": ensure_aware(fence.updated_at).isoformat(),
    }


@router.get("/live")
def live(db: Session = Depends(get_db), user: User = Depends(require_roles(Role.farmer))):
    farm = db.get(Farm, user.farm_id) if user.farm_id else None
    if farm is None:
        raise HTTPException(400, "No farm linked to this account")
    fence = _get_or_create_fence(db, farm)

    animals = db.execute(
        select(Animal).where(Animal.farm_id == farm.id, Animal.status == "active")
    ).scalars().all()
    gps_simulator.advance_positions(db, animals, fences={farm.id: fence}, hours_back=2)

    out = []
    for animal in animals:
        pos = db.execute(
            select(AnimalPosition)
            .where(AnimalPosition.animal_id == animal.id)
            .order_by(AnimalPosition.recorded_at.desc())
            .limit(1)
        ).scalar_one_or_none()
        if pos is None:
            continue
        gps_simulator.sync_breach_alerts(db, animal, fence)
        # breach state vs the CURRENT fence -- stored flags may predate edits
        dist = haversine_m(pos.lat, pos.lng, fence.center_lat, fence.center_lng)
        inside = (not fence.enabled) or dist <= fence.radius_m
        out.append(
            {
                "animal_id": animal.id,
                "tag_id": animal.tag_id,
                "species": getattr(animal.species, "value", str(animal.species)),
                "breed": animal.breed,
                "lat": pos.lat,
                "lng": pos.lng,
                "recorded_at": ensure_aware(pos.recorded_at).isoformat(),
                "recorded_at_display": ist_str(ensure_aware(pos.recorded_at)),
                "speed_kmh": pos.speed_kmh,
                "distance_from_center_m": dist,
                "inside_geofence": inside,
                "breach": not inside and fence.enabled,
            }
        )
    db.commit()
    return {"farm_id": farm.id, "geofence": _serialize_fence(fence), "animals": out}


@router.get("/geofence")
def get_geofence(db: Session = Depends(get_db), user: User = Depends(require_roles(Role.farmer))):
    farm = db.get(Farm, user.farm_id) if user.farm_id else None
    if farm is None:
        raise HTTPException(400, "No farm linked to this account")
    return _serialize_fence(_get_or_create_fence(db, farm))


@router.put("/geofence")
def put_geofence(
    payload: GeofenceIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.farmer)),
):
    farm = db.get(Farm, user.farm_id) if user.farm_id else None
    if farm is None:
        raise HTTPException(400, "No farm linked to this account")
    fence = _get_or_create_fence(db, farm)
    fence.center_lat = payload.center_lat
    fence.center_lng = payload.center_lng
    fence.radius_m = payload.radius_m
    fence.enabled = payload.enabled
    fence.updated_at = utcnow()

    # re-evaluate every animal against the new boundary immediately
    animals = db.execute(
        select(Animal).where(Animal.farm_id == farm.id, Animal.status == "active")
    ).scalars().all()
    gps_simulator.advance_positions(db, animals, fences={farm.id: fence}, hours_back=2)
    for animal in animals:
        gps_simulator.sync_breach_alerts(db, animal, fence)
    db.commit()
    return _serialize_fence(fence)


@router.get("/history")
def history(
    animal_id: int,
    minutes: int = 120,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.farmer)),
):
    animal = db.get(Animal, animal_id)
    if not animal:
        raise HTTPException(404, "Animal not found")
    ensure_farm_access(user, animal.farm_id)
    minutes = min(minutes, 24 * 60)

    # make sure points exist even if /live was never polled on this farm
    farm = db.get(Farm, animal.farm_id)
    fence = _get_or_create_fence(db, farm)
    gps_simulator.advance_positions(
        db, [animal], fences={animal.farm_id: fence},
        hours_back=max(1, min(minutes // 60 + 1, 6)),
    )

    cutoff = ensure_aware(utcnow()) - timedelta(minutes=minutes)
    points = db.execute(
        select(AnimalPosition)
        .where(
            AnimalPosition.animal_id == animal_id,
            AnimalPosition.recorded_at >= cutoff,
        )
        .order_by(AnimalPosition.recorded_at.asc())
        .limit(500)
    ).scalars().all()
    return [
        {
            "lat": p.lat,
            "lng": p.lng,
            "recorded_at": ensure_aware(p.recorded_at).isoformat(),
            "inside_geofence": bool(p.inside_geofence),
        }
        for p in points
    ]
