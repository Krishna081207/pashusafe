from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.utils.timeutil import utcnow


class ModelRegistry(Base):
    __tablename__ = "model_registry"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)  # mrl_risk_clf | outbreak_risk_clf
    version: Mapped[int] = mapped_column(Integer, default=1)
    artifact_path: Mapped[str] = mapped_column(Text)
    trained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    metrics_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class MlPrediction(Base):
    """Cached per-animal risk scores (refreshed by /ml endpoints and seed)."""

    __tablename__ = "ml_predictions"

    id: Mapped[int] = mapped_column(primary_key=True)
    animal_id: Mapped[int] = mapped_column(ForeignKey("animals.id"), index=True)
    model_name: Mapped[str] = mapped_column(String(80))
    risk: Mapped[float] = mapped_column(Float)
    band: Mapped[str] = mapped_column(String(10))  # low | medium | high
    features_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    predicted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
