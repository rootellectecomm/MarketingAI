from sqlalchemy import text

from app import models  # noqa: F401
from app.database.base import Base
from app.database.session import get_engine

# Import models so metadata is populated.

_schema_ready = False


async def ensure_schema() -> None:
    global _schema_ready
    if _schema_ready:
        return
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("SELECT 1"))
    _schema_ready = True
