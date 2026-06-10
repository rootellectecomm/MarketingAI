"""campaign conversion flow

Revision ID: 0005_campaign_conversion_flow
Revises: 0004_webhook_signature_nullable
Create Date: 2026-06-10
"""

import sqlalchemy as sa

from alembic import op

revision = "0005_campaign_conversion_flow"
down_revision = "0004_webhook_signature_nullable"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("campaigns", sa.Column("platform", sa.String(length=32), nullable=False, server_default="both"))
    op.add_column("campaigns", sa.Column("post_id", sa.String(length=255), nullable=True))
    op.add_column("campaigns", sa.Column("product_key", sa.String(length=128), nullable=True))
    op.add_column("campaigns", sa.Column("product_name", sa.String(length=255), nullable=True))
    op.add_column("campaigns", sa.Column("product_link", sa.Text(), nullable=True))
    op.add_column("campaigns", sa.Column("followup_link", sa.Text(), nullable=True))
    op.add_column("campaigns", sa.Column("whatsapp_link", sa.Text(), nullable=True))
    op.add_column(
        "campaigns",
        sa.Column("public_reply_template", sa.Text(), nullable=False, server_default="Sent you the details in DM."),
    )
    op.add_column("campaigns", sa.Column("dm_template", sa.Text(), nullable=False, server_default=""))
    op.add_column("campaigns", sa.Column("ai_prompt_override", sa.Text(), nullable=True))
    op.add_column("campaigns", sa.Column("ai_followup_enabled", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.create_index("ix_campaigns_platform", "campaigns", ["platform"])
    op.create_index("ix_campaigns_post_id", "campaigns", ["post_id"])
    op.create_index("ix_campaigns_product_key", "campaigns", ["product_key"])

    op.add_column("leads", sa.Column("platform", sa.String(length=64), nullable=False, server_default="instagram"))
    op.add_column("leads", sa.Column("product_interest", sa.String(length=255), nullable=True))
    op.add_column("leads", sa.Column("intent_level", sa.String(length=32), nullable=False, server_default="low"))
    op.add_column("leads", sa.Column("last_message", sa.Text(), nullable=True))
    op.add_column("leads", sa.Column("source_campaign_id", sa.String(length=36), nullable=True))
    op.add_column("leads", sa.Column("conversion_stage", sa.String(length=64), nullable=False, server_default="new"))
    op.create_index("ix_leads_platform", "leads", ["platform"])
    op.create_index("ix_leads_product_interest", "leads", ["product_interest"])
    op.create_index("ix_leads_intent_level", "leads", ["intent_level"])
    op.create_index("ix_leads_source_campaign_id", "leads", ["source_campaign_id"])
    op.create_index("ix_leads_conversion_stage", "leads", ["conversion_stage"])
    op.create_foreign_key("fk_leads_source_campaign_id_campaigns", "leads", "campaigns", ["source_campaign_id"], ["id"])

    op.create_table(
        "campaign_events",
        sa.Column("campaign_id", sa.String(length=36), nullable=False),
        sa.Column("platform", sa.String(length=64), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=True),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("comment_id", sa.String(length=255), nullable=True),
        sa.Column("message_id", sa.String(length=255), nullable=True),
        sa.Column("matched_keyword", sa.String(length=255), nullable=True),
        sa.Column("user_text", sa.Text(), nullable=False),
        sa.Column("ai_intent", sa.String(length=128), nullable=True),
        sa.Column("lead_score", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_campaign_events_campaign_id", "campaign_events", ["campaign_id"])
    op.create_index("ix_campaign_events_platform", "campaign_events", ["platform"])
    op.create_index("ix_campaign_events_source_type", "campaign_events", ["source_type"])
    op.create_index("ix_campaign_events_user_id", "campaign_events", ["user_id"])
    op.create_index("ix_campaign_events_username", "campaign_events", ["username"])
    op.create_index("ix_campaign_events_comment_id", "campaign_events", ["comment_id"])
    op.create_index("ix_campaign_events_message_id", "campaign_events", ["message_id"])
    op.create_index("ix_campaign_events_matched_keyword", "campaign_events", ["matched_keyword"])
    op.create_index("ix_campaign_events_ai_intent", "campaign_events", ["ai_intent"])
    op.create_index("ix_campaign_events_status", "campaign_events", ["status"])
    op.create_index("ix_campaign_event_comment_unique", "campaign_events", ["campaign_id", "comment_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_campaign_event_comment_unique", table_name="campaign_events")
    op.drop_index("ix_campaign_events_status", table_name="campaign_events")
    op.drop_index("ix_campaign_events_ai_intent", table_name="campaign_events")
    op.drop_index("ix_campaign_events_matched_keyword", table_name="campaign_events")
    op.drop_index("ix_campaign_events_message_id", table_name="campaign_events")
    op.drop_index("ix_campaign_events_comment_id", table_name="campaign_events")
    op.drop_index("ix_campaign_events_username", table_name="campaign_events")
    op.drop_index("ix_campaign_events_user_id", table_name="campaign_events")
    op.drop_index("ix_campaign_events_source_type", table_name="campaign_events")
    op.drop_index("ix_campaign_events_platform", table_name="campaign_events")
    op.drop_index("ix_campaign_events_campaign_id", table_name="campaign_events")
    op.drop_table("campaign_events")

    op.drop_constraint("fk_leads_source_campaign_id_campaigns", "leads", type_="foreignkey")
    op.drop_index("ix_leads_conversion_stage", table_name="leads")
    op.drop_index("ix_leads_source_campaign_id", table_name="leads")
    op.drop_index("ix_leads_intent_level", table_name="leads")
    op.drop_index("ix_leads_product_interest", table_name="leads")
    op.drop_index("ix_leads_platform", table_name="leads")
    op.drop_column("leads", "conversion_stage")
    op.drop_column("leads", "source_campaign_id")
    op.drop_column("leads", "last_message")
    op.drop_column("leads", "intent_level")
    op.drop_column("leads", "product_interest")
    op.drop_column("leads", "platform")

    op.drop_index("ix_campaigns_product_key", table_name="campaigns")
    op.drop_index("ix_campaigns_post_id", table_name="campaigns")
    op.drop_index("ix_campaigns_platform", table_name="campaigns")
    op.drop_column("campaigns", "ai_followup_enabled")
    op.drop_column("campaigns", "ai_prompt_override")
    op.drop_column("campaigns", "dm_template")
    op.drop_column("campaigns", "public_reply_template")
    op.drop_column("campaigns", "whatsapp_link")
    op.drop_column("campaigns", "followup_link")
    op.drop_column("campaigns", "product_link")
    op.drop_column("campaigns", "product_name")
    op.drop_column("campaigns", "product_key")
    op.drop_column("campaigns", "post_id")
    op.drop_column("campaigns", "platform")
