"""allow unknown webhook signature state

Revision ID: 0004_webhook_signature_nullable
Revises: 0003_giveaway_automation
Create Date: 2026-06-10
"""

from alembic import op
import sqlalchemy as sa

revision = "0004_webhook_signature_nullable"
down_revision = "0003_giveaway_automation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("webhook_logs", "signature_valid", existing_type=sa.Boolean(), nullable=True)


def downgrade() -> None:
    op.alter_column("webhook_logs", "signature_valid", existing_type=sa.Boolean(), nullable=False)
