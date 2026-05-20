from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.database.session import get_sessionmaker
from app.models.entities import Funnel, FunnelStep, Lead, LeadFunnelState
from app.services.provider_factory import get_whatsapp_provider


DEFAULT_FUNNEL_STEPS = [
    ("instagram_dm", 0, "Thanks for reaching out. What wellness goal matters most to you right now — sleep, hormones, energy, or something else?"),
    ("instagram_dm", 24, "Sharing a gentle note — happy to explain ingredients and what may suit your routine, without any pressure."),
    ("whatsapp_message", 48, "Hi — continuing here on WhatsApp. I can share calm, science-backed guidance whenever you're ready."),
    ("whatsapp_message", 72, "A few customers found this helpful: start with education, then choose what feels right. Want a simple recommendation?"),
    ("whatsapp_message", 120, "If you're closer to deciding, I can help with product fit, usage, or order questions — no rush at all."),
]


class FunnelRunner:
    async def ensure_default_funnel(self, session: AsyncSession) -> Funnel:
        existing = await session.scalar(select(Funnel).where(Funnel.name == "Default Wellness Journey"))
        if existing:
            return existing

        funnel = Funnel(
            name="Default Wellness Journey",
            status="active",
            description="Awareness → IG DM → WhatsApp nurture → education → soft purchase",
        )
        session.add(funnel)
        await session.flush()

        for index, (channel, delay_hours, template) in enumerate(DEFAULT_FUNNEL_STEPS):
            session.add(
                FunnelStep(
                    funnel_id=funnel.id,
                    step_order=index,
                    channel=channel,
                    delay_hours=delay_hours,
                    message_template=template,
                    min_lead_score=0,
                    max_lead_score=100,
                )
            )
        await session.flush()
        return funnel

    async def enroll_lead(self, session: AsyncSession, lead: Lead, funnel: Funnel | None = None) -> LeadFunnelState | None:
        funnel = funnel or await self.ensure_default_funnel(session)
        state = await session.scalar(
            select(LeadFunnelState).where(LeadFunnelState.lead_id == lead.id, LeadFunnelState.funnel_id == funnel.id)
        )
        if state:
            return state

        first_step = await session.scalar(
            select(FunnelStep)
            .where(FunnelStep.funnel_id == funnel.id)
            .order_by(FunnelStep.step_order.asc())
            .limit(1)
        )
        if not first_step:
            return None

        state = LeadFunnelState(
            lead_id=lead.id,
            funnel_id=funnel.id,
            current_step_order=first_step.step_order,
            next_run_at=datetime.now(UTC) + timedelta(hours=first_step.delay_hours),
            status="active",
        )
        session.add(state)
        await session.flush()
        return state

    async def process_due_steps(self) -> None:
        async with get_sessionmaker()() as session:
            await self.ensure_default_funnel(session)
            now = datetime.now(UTC)
            states = (
                await session.execute(
                    select(LeadFunnelState).where(
                        LeadFunnelState.status == "active",
                        LeadFunnelState.next_run_at.is_not(None),
                        LeadFunnelState.next_run_at <= now,
                    )
                )
            ).scalars().all()

            for state in states:
                lead = await session.get(Lead, state.lead_id)
                if not lead:
                    continue

                step = await session.scalar(
                    select(FunnelStep).where(
                        FunnelStep.funnel_id == state.funnel_id,
                        FunnelStep.step_order == state.current_step_order,
                    )
                )
                if not step or not (step.min_lead_score <= lead.score <= step.max_lead_score):
                    state.status = "skipped"
                    continue

                if step.channel == "whatsapp_message" and lead.phone:
                    provider = get_whatsapp_provider()
                    settings = get_settings()
                    if lead.whatsapp_opt_in:
                        await provider.send_whatsapp_text(lead.phone, step.message_template)
                    else:
                        await provider.send_whatsapp_template(
                            lead.phone,
                            settings.whatsapp_opt_in_template_name,
                            [step.message_template[:200]],
                        )
                        lead.whatsapp_opt_in = True

                next_step = await session.scalar(
                    select(FunnelStep)
                    .where(FunnelStep.funnel_id == state.funnel_id, FunnelStep.step_order > state.current_step_order)
                    .order_by(FunnelStep.step_order.asc())
                    .limit(1)
                )
                if next_step:
                    state.current_step_order = next_step.step_order
                    state.next_run_at = datetime.now(UTC) + timedelta(hours=next_step.delay_hours)
                else:
                    state.status = "completed"
                    state.next_run_at = None

            await session.commit()
