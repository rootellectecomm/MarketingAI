from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def normalize_async_database_url(database_url: str) -> tuple[URL, dict[str, Any]]:
    url = make_url(database_url)
    connect_args: dict[str, Any] = {}

    if url.drivername in {"postgres", "postgresql", "postgresql+psycopg", "postgresql+psycopg2"}:
        url = url.set(drivername="postgresql+asyncpg")

    if url.drivername == "postgresql+asyncpg":
        query = dict(url.query)
        ssl_value = query.pop("ssl", None) or query.pop("sslmode", None)
        if str(ssl_value).lower() in {"1", "true", "require", "verify-ca", "verify-full"}:
            connect_args["ssl"] = True
        url = url.set(query=query)

    return url, connect_args


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        settings = get_settings()
        database_url, connect_args = normalize_async_database_url(settings.database_url)
        _engine = create_async_engine(database_url, pool_pre_ping=True, connect_args=connect_args)
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(get_engine(), expire_on_commit=False, class_=AsyncSession)
    return _sessionmaker


async def dispose_engine() -> None:
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _sessionmaker = None


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with get_sessionmaker()() as session:
        yield session
