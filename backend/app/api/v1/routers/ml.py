from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import ensure_farm_access, get_current_user, require_roles
from app.db.session import get_db
from app.models import Animal, User
from app.services.ml import features as feat
from app.services.ml import serve
from app.services.ml.train import train_all

router = APIRouter(prefix="/ml", tags=["ml"])


@router.get("/predict/animal/{animal_id}")
def predict_animal(
    animal_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    animal = db.get(Animal, animal_id)
    if not animal:
        raise HTTPException(404, "Animal not found")
    ensure_farm_access(user, animal.farm_id)

    mrl_feats = feat.mrl_features(db, animal)
    outbreak_feats = feat.outbreak_features(db, animal)

    mrl_pred = serve.predict_mrl(mrl_feats)
    out_pred = serve.predict_outbreak(outbreak_feats) if outbreak_feats else None

    return {
        "animal_id": animal.id,
        "tag_id": animal.tag_id,
        "mrl_violation_risk": mrl_pred,
        "outbreak_risk": out_pred,
        "trained_on": "synthetic demonstration data",
    }


@router.get("/predict/farm/{farm_id}")
def predict_farm(
    farm_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Ranked list -- highest-risk animals first (dashboard 'watchlist')."""
    ensure_farm_access(user, farm_id)
    animals = db.execute(
        select(Animal).where(Animal.farm_id == farm_id, Animal.status == "active")
    ).scalars().all()
    rows = []
    for a in animals:
        pred = serve.predict_mrl(feat.mrl_features(db, a))
        if pred is None:
            continue
        rows.append({"animal_id": a.id, "tag_id": a.tag_id, **pred})
    rows.sort(key=lambda r: -r["risk"])
    return {"farm_id": farm_id, "watchlist": rows[:15], "trained_on": "synthetic demonstration data"}


@router.get("/model/info")
def model_info(db: Session = Depends(get_db)):
    return serve.model_info(db)


@router.post("/train")
def retrain(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    metrics = train_all(db)
    serve.joblib_load.cache_clear()
    return {"ok": True, "metrics": metrics}
