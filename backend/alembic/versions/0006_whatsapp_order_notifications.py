"""whatsapp order notifications

Revision ID: 0006_whatsapp_order_notifications
Revises: 0005_campaign_conversion_flow
Create Date: 2026-10-31
"""

import sqlalchemy as sa

from alembic import op

revision = "0006_whatsapp_order_notifications"
down_revision = "0005_campaign_conversion_flow"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "whatsapp_contacts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("first_name", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("transactional_opt_in", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("transactional_opt_in_source", sa.String(length=64), nullable=True),
        sa.Column("marketing_opt_in", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("marketing_opt_in_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("marketing_opt_in_source", sa.String(length=64), nullable=True),
        sa.Column("opted_out_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_inbound_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_whatsapp_contacts_phone", "whatsapp_contacts", ["phone"], unique=True)
    op.create_index("ix_whatsapp_contacts_marketing_opt_in", "whatsapp_contacts", ["marketing_opt_in"])

    op.create_table(
        "whatsapp_notifications",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("template_name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False, server_default="utility"),
        sa.Column("order_external_id", sa.String(length=255), nullable=True),
        sa.Column("body_params", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("button_params", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="scheduled"),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("provider_message_id", sa.String(length=255), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_whatsapp_notifications_idempotency_key", "whatsapp_notifications", ["idempotency_key"], unique=True)
    for column in ("phone", "kind", "order_external_id", "status", "scheduled_for", "provider_message_id"):
        op.create_index(f"ix_whatsapp_notifications_{column}", "whatsapp_notifications", [column])


def downgrade() -> None:
    op.drop_table("whatsapp_notifications")
    op.drop_table("whatsapp_contacts")
