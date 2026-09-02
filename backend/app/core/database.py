from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase
from app.core.config import get_settings

settings = get_settings()

db_url = settings.database_url
# Select async drivers for both local SQLite and PostgreSQL deployments.
if db_url.startswith("sqlite://") and not db_url.startswith("sqlite+aiosqlite://"):
    db_url = db_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
elif db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif db_url.startswith("postgresql://") and not db_url.startswith("postgresql+asyncpg://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

connect_args: dict = {}
if db_url.startswith("postgresql+asyncpg://"):
    asyncpg_url = make_url(db_url)
    sslmode = asyncpg_url.query.get("sslmode")
    if sslmode:
        connect_args["ssl"] = sslmode != "disable"
    # Render/libpq URLs may include parameters that asyncpg does not accept.
    db_url = str(asyncpg_url.difference_update_query(["sslmode", "channel_binding"]))

engine = create_async_engine(db_url, echo=False, future=True, connect_args=connect_args)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session