from collections.abc import AsyncGenerator

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import settings


def _async_db_url(url: str) -> str:
    """Swap a sync Postgres driver (psycopg2 / none) for asyncpg."""
    parsed = make_url(url)
    if parsed.drivername in ("postgresql", "postgresql+psycopg2"):
        parsed = parsed.set(drivername="postgresql+asyncpg")
    return parsed.render_as_string(hide_password=False)


engine: AsyncEngine = create_async_engine(_async_db_url(settings.DB_URL), echo=True)


async def get_session() -> AsyncGenerator[AsyncSession]:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session


async def db_init() -> None:
    from app.database import models  # noqa: F401  (registers tables on SQLModel.metadata)

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
