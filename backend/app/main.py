from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.core.config import get_settings
from app.core.database import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure tables exist without breaking on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    settings = get_settings()
    mode = "claude" if settings.anthropic_api_key else "offline"
    print(f"[pashusafe] starting | env={settings.environment} | assistant={mode}")
    yield


settings = get_settings()

app = FastAPI(
    title="PashuSafe API",
    description=(
        "Digital livestock farm management portal for Antimicrobial Usage (AMU) "
        "tracking and Maximum Residue Limit (MRL) compliance. "
        "Roles: farmer / vet / regulator / admin."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok", "service": "pashusafe", "environment": settings.environment}