import structlog
from sqlalchemy import text

from app import models  # noqa: F401
from app.database.base import Base
from app.database.session import get_engine

# Import models so metadata is populated.

logger = structlog.get_logger(__name__)
_schema_ready = False


# Idempotent, Postgres-safe column reconciliation. ``create_all`` only creates
# missing tables; it never adds columns to tables that already exist. Databases
# provisioned before later model/migration changes therefore drift and break
# inserts/selects (e.g. the campaigns conversion-flow columns). These statements
# bring any pre-existing table back in line without depending on Alembic being
# bundled or runnable in the serverless deployment.
_RECONCILE_STATEMENTS: tuple[str, ...] = (
    # campaigns conversion-flow columns (migration 0005)
    "ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS platform VARCHAR(32) NOT NULL DEFAULT 'both'",
    "ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS post_id VARCHAR(255)",
    "ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS product_key VARCHAR(128)",
    "ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS product_name VARCHAR(255)",
    "ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS product_link TEXT",
    "ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS followup_link TEXT",
    "ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS whatsapp_link TEXT",
    "ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS product_focus JSON NOT NULL DEFAULT '[]'::json",
    "ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS keyword_triggers JSON NOT NULL DEFAULT '[]'::json",
    "ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS public_reply_template TEXT NOT NULL DEFAULT 'Sent you the details in DM.'",
    "ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS dm_template TEXT NOT NULL DEFAULT ''",
    "ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS ai_prompt_override TEXT",
    "ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS public_reply_enabled BOOLEAN NOT NULL DEFAULT true",
    "ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS dm_enabled BOOLEAN NOT NULL DEFAULT true",
    "ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS whatsapp_followup_enabled BOOLEAN NOT NULL DEFAULT false",
    "ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS ai_followup_enabled BOOLEAN NOT NULL DEFAULT true",
    "ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS metadata_json JSON NOT NULL DEFAULT '{}'::json",
    # leads conversion-flow columns (migration 0005)
    "ALTER TABLE leads ADD COLUMN IF NOT EXISTS platform VARCHAR(64) NOT NULL DEFAULT 'instagram'",
    "ALTER TABLE leads ADD COLUMN IF NOT EXISTS product_interest VARCHAR(255)",
    "ALTER TABLE leads ADD COLUMN IF NOT EXISTS intent_level VARCHAR(32) NOT NULL DEFAULT 'low'",
    "ALTER TABLE leads ADD COLUMN IF NOT EXISTS last_message TEXT",
    "ALTER TABLE leads ADD COLUMN IF NOT EXISTS source_campaign_id VARCHAR(36)",
    "ALTER TABLE leads ADD COLUMN IF NOT EXISTS conversion_stage VARCHAR(64) NOT NULL DEFAULT 'new'",
    # webhook signature may be unknown when the WhatsApp secret is unset (migration 0004)
    "ALTER TABLE webhook_logs ALTER COLUMN signature_valid DROP NOT NULL",
)


async def reconcile_schema() -> None:
    """Apply idempotent column fixes to existing Postgres tables."""
    engine = get_engine()
    if engine.dialect.name != "postgresql":
        return
    for statement in _RECONCILE_STATEMENTS:
        try:
            async with engine.begin() as conn:
                await conn.execute(text(statement))
        except Exception as exc:  # noqa: BLE001 - reconcile must never abort startup
            logger.warning("schema_reconcile_statement_failed", statement=statement, error=str(exc))


async def ensure_schema() -> None:
    global _schema_ready
    if _schema_ready:
        return
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("SELECT 1"))
    await reconcile_schema()
    _schema_ready = True
