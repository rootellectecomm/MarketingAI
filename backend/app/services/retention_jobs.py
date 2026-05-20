from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.database.session import get_sessionmaker
from app.models.entities import Conversation, Lead, Message, Order
from app.services.funnel_runner import FunnelRunner
from app.services.provider_factory import get_whatsapp_provider


RECOVERY_MESSAGE = (
    "Just checking in — sometimes wellness decisions take time. "
    "Happy to guide if you're still exploring what may suit you."
)

RETENTION_MESSAGES = {
    0: "Thank you for trusting Rootellect. Start gently, stay consistent, and listen to your body.",
    7: "Quick check-in — how has your first week felt with the product?",
    21: "It's been a few weeks — how has your experience been? We'd love to hear if it's supporting you.",
}


class RetentionJobRunner:
    async def recover_stale_conversations(self) -> None:
        cutoff = datetime.now(UTC) - timedelta(hours=24)
        async with get_sessionmaker()() as session:
            conversations = (
                await session.execute(
                    select(Conversation).where(
                        Conversation.is_open.is_(True),
                        Conversation.last_message_at.is_not(None),
                        Conversation.last_message_at <= cutoff,
                    )
                )
            ).scalars().all()

            for conversation in conversations[:50]:
                last_outbound = await session.scalar(
                    select(Message)
                    .where(Message.conversation_id == conversation.id, Message.direction == "outbound")
                    .order_by(Message.created_at.desc())
                    .limit(1)
                )
                if last_outbound and last_outbound.created_at > cutoff:
                    continue

                lead = await session.scalar(
                    select(Lead).where(
                        Lead.external_user_id == conversation.external_user_id,
                        Lead.source_channel.in_(["instagram", "whatsapp"]),
                    )
                )
                if not lead:
                    continue

                if lead.phone and lead.whatsapp_opt_in:
                    provider = get_whatsapp_provider()
                    result = await provider.send_whatsapp_text(lead.phone, RECOVERY_MESSAGE)
                    if result.ok:
                        session.add(
                            Message(
                                conversation_id=conversation.id,
                                direction="outbound",
                                body=RECOVERY_MESSAGE,
                                channel="whatsapp_message",
                                metadata_json={"automated": True, "job": "conversation_recovery"},
                            )
                        )
                conversation.last_message_at = datetime.now(UTC)

            await session.commit()

    async def process_touchpoints(self) -> None:
        async with get_sessionmaker()() as session:
            orders = (
                await session.execute(
                    select(Order).where(Order.status.in_(["paid", "completed", "fulfilled"]))
                )
            ).scalars().all()

            settings = get_settings()
            provider = get_whatsapp_provider()

            for order in orders[:100]:
                if not order.customer_phone or not order.lead_id:
                    continue
                lead = await session.get(Lead, order.lead_id)
                if not lead:
                    continue

                purchased_at = order.created_at
                if not purchased_at:
                    continue
                days = (datetime.now(UTC) - purchased_at).days
                for target_day, message in RETENTION_MESSAGES.items():
                    if days != target_day:
                        continue
                    meta = order.metadata_json or {}
                    sent_key = f"retention_day_{target_day}"
                    if meta.get(sent_key):
                        break
                    if lead.whatsapp_opt_in:
                        await provider.send_whatsapp_text(order.customer_phone, message)
                    else:
                        await provider.send_whatsapp_template(
                            order.customer_phone,
                            settings.whatsapp_opt_in_template_name,
                            [message[:200]],
                        )
                    meta[sent_key] = datetime.now(UTC).isoformat()
                    order.metadata_json = meta
                    break

            await session.commit()

    async def enroll_new_leads(self, session: AsyncSession, lead: Lead) -> None:
        await FunnelRunner().enroll_lead(session, lead)
