"""giveaway automation tables

Revision ID: 0003_giveaway_automation
Revises: 0002_funnels_commerce
Create Date: 2026-05-20
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_giveaway_automation"
down_revision = "0002_funnels_commerce"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "instagram_posts",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("instagram_account_id", sa.String(), sa.ForeignKey("instagram_accounts.id"), nullable=True),
        sa.Column("media_id", sa.String(length=255), nullable=False),
        sa.Column("media_type", sa.String(length=64), nullable=True),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column("thumbnail_url", sa.Text(), nullable=True),
        sa.Column("permalink", sa.Text(), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
    )
    op.create_index("ix_instagram_posts_instagram_account_id", "instagram_posts", ["instagram_account_id"])
    op.create_index("ix_instagram_posts_media_id", "instagram_posts", ["media_id"], unique=True)

    op.create_table(
        "giveaway_automations",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("instagram_account_id", sa.String(), sa.ForeignKey("instagram_accounts.id"), nullable=True),
        sa.Column("instagram_post_id", sa.String(), sa.ForeignKey("instagram_posts.id"), nullable=True),
        sa.Column("media_id", sa.String(length=255), nullable=True),
        sa.Column("media_permalink", sa.Text(), nullable=True),
        sa.Column("trigger_type", sa.String(length=64), nullable=False),
        sa.Column("trigger_keywords", sa.JSON(), nullable=False),
        sa.Column("public_reply_text", sa.Text(), nullable=False),
        sa.Column("public_reply_variations", sa.JSON(), nullable=False),
        sa.Column("dm_message_text", sa.Text(), nullable=False),
        sa.Column("follow_button_text", sa.String(length=128), nullable=False),
        sa.Column("reply_limit", sa.Integer(), nullable=False),
        sa.Column("cooldown_hours", sa.Integer(), nullable=False),
        sa.Column("exclusion_keywords", sa.JSON(), nullable=False),
        sa.Column("brand_signature", sa.String(length=255), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
    )
    op.create_index("ix_giveaway_automations_name", "giveaway_automations", ["name"])
    op.create_index("ix_giveaway_automations_status", "giveaway_automations", ["status"])
    op.create_index("ix_giveaway_automations_instagram_account_id", "giveaway_automations", ["instagram_account_id"])
    op.create_index("ix_giveaway_automations_instagram_post_id", "giveaway_automations", ["instagram_post_id"])
    op.create_index("ix_giveaway_automations_media_id", "giveaway_automations", ["media_id"])

    op.create_table(
        "giveaway_contents",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("automation_id", sa.String(), sa.ForeignKey("giveaway_automations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content_type", sa.String(length=64), nullable=False),
        sa.Column("coupon_code", sa.String(length=255), nullable=True),
        sa.Column("message_text", sa.Text(), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("carousel_slides", sa.JSON(), nullable=False),
        sa.Column("cta_label", sa.String(length=128), nullable=True),
        sa.Column("cta_url", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("unique_coupon_enabled", sa.Boolean(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
    )
    op.create_index("ix_giveaway_contents_automation_id", "giveaway_contents", ["automation_id"])

    op.create_table(
        "giveaway_participants",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("automation_id", sa.String(), sa.ForeignKey("giveaway_automations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("comment_id", sa.String(), sa.ForeignKey("comments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("social_event_id", sa.String(), sa.ForeignKey("social_events.id", ondelete="SET NULL"), nullable=True),
        sa.Column("lead_id", sa.String(), sa.ForeignKey("leads.id", ondelete="SET NULL"), nullable=True),
        sa.Column("instagram_user_id", sa.String(length=255), nullable=False),
        sa.Column("instagram_username", sa.String(length=255), nullable=True),
        sa.Column("comment_text", sa.Text(), nullable=False),
        sa.Column("trigger_matched", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("reward_sent", sa.Boolean(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
    )
    op.create_index("ix_giveaway_participants_automation_id", "giveaway_participants", ["automation_id"])
    op.create_index("ix_giveaway_participants_comment_id", "giveaway_participants", ["comment_id"])
    op.create_index("ix_giveaway_participants_lead_id", "giveaway_participants", ["lead_id"])
    op.create_index("ix_giveaway_participants_instagram_user_id", "giveaway_participants", ["instagram_user_id"])
    op.create_index("ix_giveaway_participants_instagram_username", "giveaway_participants", ["instagram_username"])
    op.create_index("ix_giveaway_participants_status", "giveaway_participants", ["status"])
    op.create_index(
        "ix_giveaway_participant_unique",
        "giveaway_participants",
        ["automation_id", "instagram_user_id"],
        unique=True,
    )

    op.create_table(
        "automation_event_logs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("automation_type", sa.String(length=64), nullable=False),
        sa.Column("automation_id", sa.String(length=36), nullable=True),
        sa.Column("participant_id", sa.String(length=36), nullable=True),
        sa.Column("event_name", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
    )
    op.create_index("ix_automation_event_logs_automation_type", "automation_event_logs", ["automation_type"])
    op.create_index("ix_automation_event_logs_automation_id", "automation_event_logs", ["automation_id"])
    op.create_index("ix_automation_event_logs_participant_id", "automation_event_logs", ["participant_id"])
    op.create_index("ix_automation_event_logs_event_name", "automation_event_logs", ["event_name"])
    op.create_index("ix_automation_event_logs_status", "automation_event_logs", ["status"])

    op.create_table(
        "global_giveaway_settings",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("default_public_reply_text", sa.Text(), nullable=False),
        sa.Column("public_reply_variations", sa.JSON(), nullable=False),
        sa.Column("comment_reply_limit", sa.Integer(), nullable=False),
        sa.Column("exclusion_keywords", sa.JSON(), nullable=False),
        sa.Column("cooldown_hours", sa.Integer(), nullable=False),
        sa.Column("fallback_dm_text", sa.Text(), nullable=False),
        sa.Column("brand_signature", sa.String(length=255), nullable=False),
        sa.Column("opt_out_keywords", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("global_giveaway_settings")
    op.drop_table("automation_event_logs")
    op.drop_table("giveaway_participants")
    op.drop_table("giveaway_contents")
    op.drop_table("giveaway_automations")
    op.drop_table("instagram_posts")
