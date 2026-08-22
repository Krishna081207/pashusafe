from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, scoped_farm_ids
from app.db.session import get_db
from app.models import User
from app.services.assistant import claude_agent, offline_brain

router = APIRouter(prefix="/assistant", tags=["assistant"])


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class ChatOut(BaseModel):
    answer: str
    mode: str  # "claude" | "offline"
    sources: list[str] = []


@router.post("/chat", response_model=ChatOut)
def chat(
    payload: ChatIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Ask about your farm data. Uses Claude when ANTHROPIC_API_KEY is set,
    otherwise the deterministic offline brain -- both scoped to your role."""
    farm_ids = scoped_farm_ids(user)

    if claude_agent.available():
        try:
            text, sources = claude_agent.answer(db, farm_ids, payload.message, user.role.value)
            return ChatOut(answer=text, mode="claude", sources=sources)
        except Exception:
            # fall through to offline so the demo never breaks
            pass

    return ChatOut(
        answer=offline_brain.answer(db, farm_ids, payload.message),
        mode="offline",
        sources=[],
    )


@router.get("/suggestions")
def get_suggestions(_: User = Depends(get_current_user)):
    return {"suggestions": offline_brain.suggestions(), "mode": "claude" if claude_agent.available() else "offline"}
