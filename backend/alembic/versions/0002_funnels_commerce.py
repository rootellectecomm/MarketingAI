"""funnels and commerce tables

Revision ID: 0002_funnels_commerce
Revises: 0001_initial_schema
Create Date: 2026-05-20
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_funnels_commerce"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "funnels",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
    )
    op.create_table(
        "funnel_steps",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("funnel_id", sa.String(), sa.ForeignKey("funnels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("channel", sa.String(length=64), nullable=False),
        sa.Column("delay_hours", sa.Integer(), nullable=False),
        sa.Column("message_template", sa.Text(), nullable=False),
        sa.Column("min_lead_score", sa.Integer(), nullable=False),
        sa.Column("max_lead_score", sa.Integer(), nullable=False),
        sa.Column("lifecycle_stage", sa.String(length=64), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
    )
    op.create_table(
        "lead_funnel_states",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lead_id", sa.String(), sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("funnel_id", sa.String(), sa.ForeignKey("funnels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("current_step_order", sa.Integer(), nullable=False),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
    )
    op.create_index("ix_lead_funnel_unique", "lead_funnel_states", ["lead_id", "funnel_id"], unique=True)
    op.create_table(
        "orders",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("external_order_id", sa.String(length=255), nullable=False),
        sa.Column("lead_id", sa.String(), sa.ForeignKey("leads.id", ondelete="SET NULL"), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("total_amount", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("customer_email", sa.String(length=255), nullable=True),
        sa.Column("customer_phone", sa.String(length=64), nullable=True),
        sa.Column("line_items", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
    )
    op.create_index("ix_orders_external_order_id", "orders", ["external_order_id"], unique=True)
    op.create_table(
        "cart_abandonments",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("external_cart_id", sa.String(length=255), nullable=False),
        sa.Column("lead_id", sa.String(), sa.ForeignKey("leads.id", ondelete="SET NULL"), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("checkout_url", sa.Text(), nullable=True),
        sa.Column("recovery_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
    )
    op.create_index("ix_cart_abandonments_external_cart_id", "cart_abandonments", ["external_cart_id"], unique=True)


def downgrade() -> None:
    op.drop_table("cart_abandonments")
    op.drop_table("orders")
    op.drop_table("lead_funnel_states")
    op.drop_table("funnel_steps")
    op.drop_table("funnels")
