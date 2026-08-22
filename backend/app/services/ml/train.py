"""Train both demo models at seed time on SYNTHETIC data.

Honesty note (surfaced in UI + README): these models are trained purely on
synthetic demonstration data -- no field data. They exist to demonstrate the
predictive pipeline, not to make clinical claims.
"""

import json
import random
from pathlib import Path

import joblib
from sqlalchemy.orm import Session

from app.models import ModelRegistry
from app.services.ml.features import MRL_FEATURES, OUTBREAK_FEATURES, SPECIES_INDEX

ARTIFACT_DIR = Path(__file__).resolve().parents[3] / "ml_artifacts"
MRL_MODEL = "mrl_risk_clf"
OUTBREAK_MODEL = "outbreak_risk_clf"

RNG_SEED = 42


def _synthetic_mrl_dataset(n: int = 2500) -> tuple[list[list[float]], list[int]]:
    """Latent truth: risk rises with Watch/Reserve share, active-window pressure,
    past violations, and unsupervised use."""
    rng = random.Random(RNG_SEED)
    X, y = [], []
    for _ in range(n):
        feats = {
            "amu_30d": rng.expovariate(1 / 2.5),
            "amu_90d": rng.expovariate(1 / 6.0),
            "distinct_drugs_90d": rng.randint(0, 6),
            "watch_reserve_share": rng.random(),
            "days_until_clear": rng.choice([0, 0, 0, rng.uniform(0, 8)]),
            "past_violations": rng.choices([0, 1, 2, 3], weights=[80, 12, 5, 3])[0],
            "mean_course_days": rng.uniform(1, 7),
            "unsupervised_share": rng.random(),
            "herd_size": rng.randint(5, 60),
            "species_idx": rng.randrange(len(SPECIES_INDEX)),
        }
        latent = (
            -2.4
            + 1.9 * feats["watch_reserve_share"]
            + 0.55 * min(feats["amu_30d"], 8) / 2
            + 0.30 * min(feats["days_until_clear"], 8)
            + 0.85 * feats["past_violations"]
            + 0.9 * feats["unsupervised_share"]
            + rng.gauss(0, 0.55)
        )
        label = int(latent > 0)
        X.append([float(feats[k]) for k in MRL_FEATURES + ["species_idx"]])
        y.append(label)
    return X, y


def _poisson(rng: random.Random, lam: float) -> int:
    """Knuth's sampling for small lambdas (stdlib Random has no poisson)."""
    import math

    L = math.exp(-lam)
    k, p = 0, 1.0
    while True:
        p *= rng.random()
        if p <= L:
            return k
        k += 1


def _synthetic_outbreak_dataset(n: int = 2000) -> tuple[list[list[float]], list[int]]:
    rng = random.Random(RNG_SEED + 1)
    X, y = [], []
    for _ in range(n):
        fever = rng.random() < 0.35
        if fever:
            temp_z = max(0.5, rng.gauss(2.3, 0.7))
            drop = max(10, rng.gauss(38, 12))
        else:
            temp_z = max(-1.5, min(1.2, rng.gauss(0.05, 0.5)))
            drop = max(0, min(25, rng.gauss(6, 6)))
        amu = _poisson(rng, 1.5)
        spike_lam = 2.0 if (fever and rng.random() < 0.5) else 0.3
        spike = _poisson(rng, spike_lam)
        X.append([round(temp_z, 3), round(drop, 2), float(amu), float(spike)])
        y.append(int(fever))
    return X, y


def train_all(db: Session) -> dict:
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import train_test_split

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    results: dict[str, dict] = {}

    # --- MRL violation risk -------------------------------------------------
    X, y = _synthetic_mrl_dataset()
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=RNG_SEED, stratify=y)
    mrl_clf = HistGradientBoostingClassifier(random_state=RNG_SEED).fit(Xtr, ytr)
    auc_mrl = roc_auc_score(yte, mrl_clf.predict_proba(Xte)[:, 1])
    path_mrl = ARTIFACT_DIR / f"{MRL_MODEL}.joblib"
    joblib.dump({"model": mrl_clf, "features": MRL_FEATURES + ["species_idx"]}, path_mrl)

    # --- outbreak risk -------------------------------------------------------
    Xo, yo = _synthetic_outbreak_dataset()
    Xotr, Xote, yotr, yote = train_test_split(
        Xo, yo, test_size=0.2, random_state=RNG_SEED, stratify=yo
    )
    out_clf = LogisticRegression(max_iter=500).fit(Xotr, yotr)
    auc_out = roc_auc_score(yote, out_clf.predict_proba(Xote)[:, 1])
    path_out = ARTIFACT_DIR / f"{OUTBREAK_MODEL}.joblib"
    joblib.dump({"model": out_clf, "features": OUTBREAK_FEATURES}, path_out)

    for name, version, artifact, metrics in (
        (MRL_MODEL, 1, str(path_mrl), {"roc_auc": round(auc_mrl, 3), "n_train": len(y)}),
        (OUTBREAK_MODEL, 1, str(path_out), {"roc_auc": round(auc_out, 3), "n_train": len(yo)}),
    ):
        row = db.query(ModelRegistry).filter_by(name=name).one_or_none()
        if row is None:
            row = ModelRegistry(name=name)
            db.add(row)
        # column defaults apply at flush, not construction -- guard against None
        row.version = (row.version or 0) + 1
        row.artifact_path = artifact
        row.metrics_json = metrics
        results[name] = metrics
    db.commit()

    print("[ml] trained:", json.dumps(results))
    return results
