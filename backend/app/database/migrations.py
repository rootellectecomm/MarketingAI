from __future__ import annotations

from pathlib import Path

import structlog
from alembic import command
from alembic.config import Config

from app.core.config import get_settings

logger = structlog.get_logger(__name__)
_migrations_applied = False


def run_pending_migrations() -> None:
    global _migrations_applied
    if _migrations_applied:
        return

    settings = get_settings()
    backend_root = Path(__file__).resolve().parents[2]
    alembic_ini = backend_root / "alembic.ini"
    if not alembic_ini.exists():
        logger.warning("alembic_ini_missing", path=str(alembic_ini))
        return

    cfg = Config(str(alembic_ini))
    cfg.set_main_option("sqlalchemy.url", settings.database_url.replace("+asyncpg", ""))
    command.upgrade(cfg, "head")
    _migrations_applied = True
    logger.info("database_migrations_applied")
