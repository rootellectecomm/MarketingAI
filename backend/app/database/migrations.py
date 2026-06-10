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
    alembic_dir = backend_root / "alembic"
    if not alembic_ini.exists() or not alembic_dir.exists():
        logger.warning("alembic_ini_missing", ini=str(alembic_ini), scripts=str(alembic_dir))
        return

    try:
        cfg = Config(str(alembic_ini))
        # ``script_location`` is relative in alembic.ini and would otherwise be
        # resolved against the process CWD, which is not the backend dir on
        # serverless platforms. Pin it to an absolute path.
        cfg.set_main_option("script_location", str(alembic_dir))
        cfg.set_main_option("sqlalchemy.url", settings.database_url.replace("+asyncpg", ""))
        command.upgrade(cfg, "head")
        logger.info("database_migrations_applied")
    except Exception as exc:  # noqa: BLE001 - migrations are best-effort; schema reconcile is the safety net
        logger.warning("database_migrations_failed", error=str(exc))
    finally:
        # Attempt once per process. ``reconcile_schema`` guarantees the columns
        # exist even if Alembic could not run in this environment.
        _migrations_applied = True
