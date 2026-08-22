"""Lazy model loading + prediction wrappers. Endpoints degrade gracefully
(available: false) when artifacts are absent -- never a 500."""

from functools import lru_cache
from pathlib import Path

from app.services.ml.features import vectorize
from app.services.ml.train import ARTIFACT_DIR, MRL_MODEL, OUTBREAK_MODEL


def _load(name: str):
    path = ARTIFACT_DIR / f"{name}.joblib"
    if not path.exists():
        return None
    return joblib_load(path)


@lru_cache(maxsize=4)
def joblib_load(path: str):
    import joblib

    return joblib.load(Path(path))


def _band(risk: float) -> str:
    return "low" if risk < 0.33 else "medium" if risk < 0.66 else "high"


def predict_mrl(feats: dict) -> dict | None:
    bundle = _load(MRL_MODEL)
    if bundle is None:
        return None
    model, features = bundle["model"], bundle["features"]
    proba = float(model.predict_proba([vectorize(features, feats)])[0][1])
    top = _top_factors_mrl(feats)
    return {"risk": round(proba, 3), "band": _band(proba), "top_factors": top}


def _top_factors_mrl(f: dict) -> list[dict]:
    """Simple additive attribution for the UI (not SHAP -- honest and simple)."""
    contributions = [
        ("Watch/Reserve antimicrobial share", f.get("watch_reserve_share", 0) * 1.9),
        ("Past MRL violations", f.get("past_violations", 0) * 0.85),
        ("Unsupervised (no prescription) treatments", f.get("unsupervised_share", 0) * 0.9),
        ("Currently inside withdrawal window", min(f.get("days_until_clear", 0), 8) * 0.3),
        ("Treatments in last 30 days", min(f.get("amu_30d", 0), 8) * 0.27),
    ]
    contributions.sort(key=lambda kv: -kv[1])
    return [{"factor": name, "weight": round(w, 2)} for name, w in contributions[:3]]


def predict_outbreak(feats: dict) -> dict | None:
    bundle = _load(OUTBREAK_MODEL)
    if bundle is None:
        return None
    model, features = bundle["model"], bundle["features"]
    proba = float(model.predict_proba([vectorize(features, feats)])[0][1])
    top = sorted(
        [
            {"factor": "Temperature z-score (7d)", "weight": round(feats.get("temp_zscore", 0), 2)},
            {"factor": "Activity drop vs 7d mean %", "weight": round(feats.get("activity_drop_pct", 0) / 100, 2)},
            {"factor": "Treatments last 30d", "weight": round(feats.get("amu_30d", 0) / 10, 2)},
            {"factor": "Farm AMU spike (7d vs prior)", "weight": round(feats.get("farm_amu_spike", 0) / 10, 2)},
        ],
        key=lambda kv: -kv["weight"],
    )[:3]
    return {"risk": round(proba, 3), "band": _band(proba), "top_factors": top}


def model_info(db=None) -> dict:
    info = {
        "trained_on": "synthetic demonstration data",
        "disclaimer": "Demo pipeline only -- not validated on field data.",
        "models": {},
    }
    from app.models import ModelRegistry

    if db is not None:
        from app.models import ModelRegistry as MR

        for row in db.query(MR).all():
            info["models"][row.name] = {
                "version": row.version,
                "metrics": row.metrics_json,
                "trained_at": row.trained_at.isoformat() if row.trained_at else None,
            }
    return info
