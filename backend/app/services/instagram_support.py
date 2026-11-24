"""Instant, rule-based replies for Instagram DMs: customer issues and keyword triggers.

Runs before the AI pipeline so the questions people ask most often (where is my
order, refund, damaged item, price/link keywords) get a correct answer at once
instead of waiting in the review queue. It mirrors the WhatsApp experience:
order lookup, helpful self-serve answers, and a hand-off to the team (flagged
in the inbox with a ``needs_human`` tag) whenever a person has to step in.

Anything it does not recognise returns ``None`` and falls through to the AI.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import quote

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.product_knowledge import ROOTELLECT_PRODUCT_CATALOG, route_product
from app.core.config import get_settings
from app.models.entities import Campaign, Lead, Order
from app.services.campaign_matcher import CampaignMatcher
from app.services.phone_utils import extract_phone

ORDER_NUMBER_PATTERN = re.compile(r"\b(RT[-\s]?\d{3,8})\b", re.IGNORECASE)

# Order matters: the first topic whose terms appear wins. Safety comes first so a
# reaction question is never answered as a sales question.
TOPIC_TERMS: dict[str, tuple[str, ...]] = {
    "side_effect": (
        "side effect", "side-effect", "reaction", "allergy", "allergic", "rash", "itching", "vomit",
        "nausea", "dizzy", "headache after", "pregnan", "breastfeed", "lactating", "on medication",
        "medicine ke saath", "with my medicine", "thyroid medicine",
    ),
    "damaged_wrong": (
        "damaged", "broken", "leak", "wrong product", "wrong item", "different product", "missing item",
        "item missing", "seal open", "seal broken", "expired", "tuta", "toota", "galat product", "kam aaya",
    ),
    "payment": (
        "payment failed", "payment fail", "amount deducted", "money deducted", "paise kat", "paisa kat",
        "charged twice", "double charged", "transaction failed", "upi failed", "payment pending",
    ),
    "refund_return": (
        "refund", "return", "cancel", "money back", "paisa wapas", "paise wapas", "exchange", "replace",
    ),
    "order_status": (
        "where is my order", "where's my order", "order status", "track my order", "tracking", "track order",
        "not delivered", "not received", "didn't receive", "didnt receive", "haven't received", "kab aayega",
        "kab milega", "kab tak aayega", "delivery kab", "order kaha", "order kahan", "parcel", "shipment",
        "awb", "delayed", "late delivery", "still waiting",
    ),
    "human": (
        "talk to human", "real person", "customer care", "customer support", "contact number", "phone number",
        "call me", "agent", "support team", "complaint", "baat karni", "talk to someone",
    ),
    "how_to_use": (
        "how to use", "how to take", "how do i take", "dosage", "dose", "kaise le", "kaise lena", "kitne capsule",
        "how many capsule", "when to take", "before food", "after food", "empty stomach", "khali pet",
    ),
    "cod": ("cod", "cash on delivery"),
    "discount": ("coupon", "discount", "offer", "promo", "code chahiye", "any code"),
    "marketplace": ("amazon", "flipkart"),
    "results_timeline": ("how long", "kitne din", "when will i see", "results kab", "how many days"),
}

NEEDS_HUMAN_TOPICS = {"side_effect", "damaged_wrong", "payment", "refund_return", "human"}


@dataclass(slots=True)
class SupportReply:
    topic: str
    reply: str
    needs_human: bool = False
    matched_keyword: str | None = None
    campaign_id: str | None = None
    order_number: str | None = None
    tags: list[str] = field(default_factory=list)


def classify_topic(text: str) -> str | None:
    lowered = f" {text.lower()} "
    for topic, terms in TOPIC_TERMS.items():
        for term in terms:
            if len(term) <= 4:
                # Short terms (cod, awb, dose) must be whole words.
                if re.search(rf"\b{re.escape(term)}\b", lowered):
                    return topic
            elif term in lowered:
                return topic
    return None


class InstagramSupportRouter:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.matcher = CampaignMatcher()

    # ------------------------------------------------------------------ helpers
    def _wa_link(self, message: str) -> str:
        return f"https://wa.me/{self.settings.rootellect_whatsapp_number}?text={quote(message)}"

    def _track_link(self, code: str) -> str:
        return f"{self.settings.rootellect_site_url.rstrip('/')}/track-order/{code}"

    async def _find_order(self, session: AsyncSession, text: str, lead: Lead | None) -> Order | None:
        number_match = ORDER_NUMBER_PATTERN.search(text)
        conditions = []
        if number_match:
            number = re.sub(r"[\s]", "-", number_match.group(1).upper())
            if "-" not in number:
                number = f"RT-{number[2:]}"
            conditions.append(Order.external_order_id == number)
        phone = extract_phone(text) or (lead.phone if lead else None)
        if phone:
            digits = re.sub(r"\D", "", phone)
            conditions.extend(
                [Order.customer_phone == digits, Order.customer_phone == f"+{digits}", Order.customer_phone == digits[-10:]]
            )
        if not conditions:
            return None
        return await session.scalar(
            select(Order).where(or_(*conditions)).order_by(Order.created_at.desc()).limit(1)
        )

    # -------------------------------------------------------------- main entry
    async def handle(
        self,
        session: AsyncSession,
        text: str,
        lead: Lead | None,
        matched_campaigns: list[Campaign],
        last_outbound: str | None = None,
    ) -> SupportReply | None:
        clean = (text or "").strip()
        if not clean:
            return None
        topic = classify_topic(clean)
        # An order number, or a phone number sent after we asked for one, is an
        # order lookup - unless the message also names a real issue (damaged,
        # refund...). "My phone number is 98..." must not read as "talk to a human".
        asked_for_order = bool(last_outbound and "order number" in last_outbound.lower())
        has_order_ref = bool(ORDER_NUMBER_PATTERN.search(clean)) or (asked_for_order and bool(extract_phone(clean)))
        if has_order_ref and topic in {None, "human", "order_status"}:
            topic = "order_status"

        if topic:
            return await self._topic_reply(session, topic, clean, lead)

        return self._keyword_reply(clean, matched_campaigns)

    async def _topic_reply(self, session: AsyncSession, topic: str, text: str, lead: Lead | None) -> SupportReply:
        if topic == "order_status":
            order = await self._find_order(session, text, lead)
            if order:
                code = (order.metadata_json or {}).get("track_code") or order.external_order_id
                status = (order.status or "confirmed").replace("_", " ")
                return SupportReply(
                    topic=topic,
                    order_number=order.external_order_id,
                    reply=(
                        f"Found it! Order {order.external_order_id} is currently: {status}. "
                        f"Live tracking: {self._track_link(code)} "
                        "If anything looks off, reply here and our team will check it for you."
                    ),
                    tags=["order_status"],
                )
            return SupportReply(
                topic=topic,
                reply=(
                    "Happy to check that for you 🌿 Please share your order number (it starts with RT-, e.g. RT-10482) "
                    "or the phone number used at checkout. If you ordered on Amazon, tracking is in Amazon → Your Orders."
                ),
                tags=["order_status"],
            )

        if topic == "damaged_wrong":
            return SupportReply(
                topic=topic,
                needs_human=True,
                reply=(
                    "We're really sorry about this - that's not the experience we want for you. Please send your order "
                    "number and a photo of the product/package here, and our team will arrange a replacement or "
                    "resolution on priority. You can also reach us on WhatsApp: "
                    f"{self._wa_link('Hi Rootellect, I received a damaged/wrong product. Order no: ')}"
                ),
                tags=["issue", "damaged_wrong"],
            )

        if topic == "payment":
            return SupportReply(
                topic=topic,
                needs_human=True,
                reply=(
                    "Sorry for the trouble! If money was deducted but the order didn't go through, it's usually "
                    "auto-refunded by your bank within 5-7 working days. Please share your phone number or payment "
                    "reference and our team will verify it for you right away."
                ),
                tags=["issue", "payment"],
            )

        if topic == "refund_return":
            return SupportReply(
                topic=topic,
                needs_human=True,
                reply=(
                    "Sure, we'll help with that. Please share your order number (RT-...) and a line on what went wrong, "
                    "and our team will guide you through the cancellation/refund. For quicker help: "
                    f"{self._wa_link('Hi Rootellect, I need help with a refund/cancellation. Order no: ')}"
                ),
                tags=["issue", "refund_return"],
            )

        if topic == "side_effect":
            return SupportReply(
                topic=topic,
                needs_human=True,
                reply=(
                    "Thank you for telling us. If you notice any discomfort, please pause use and speak with your doctor. "
                    "If you're pregnant, breastfeeding or on medication, please check with your doctor before use. "
                    "Our team will also reach out to you personally here."
                ),
                tags=["issue", "safety"],
            )

        if topic == "human":
            return SupportReply(
                topic=topic,
                needs_human=True,
                reply=(
                    "Of course - I've passed this to our team and someone will reply here personally. "
                    f"For faster help you can also WhatsApp us: {self._wa_link('Hi Rootellect, I need help with ')}"
                ),
                tags=["human_request"],
            )

        if topic == "how_to_use":
            product = route_product(text)
            product_line = f" for {product.name}" if product else ""
            return SupportReply(
                topic=topic,
                reply=(
                    f"The recommended serving{product_line} is printed on the label - please follow it, ideally at the "
                    "same time daily, and give it a few weeks of consistent use as part of a healthy routine. "
                    "If you're on medication, pregnant or breastfeeding, check with your doctor first."
                ),
                tags=["how_to_use"],
            )

        if topic == "cod":
            return SupportReply(
                topic=topic,
                reply=(
                    "Yes, Cash on Delivery is available on rootellect.com at checkout 🌿 You'll get a WhatsApp message "
                    "to confirm your COD order. Shop here: https://www.rootellect.com"
                ),
                tags=["cod"],
            )

        if topic == "discount":
            return SupportReply(
                topic=topic,
                reply=(
                    "New to Rootellect? Sign up on rootellect.com for a welcome offer on your first order 🌿 "
                    "Any live offers are applied at checkout: https://www.rootellect.com"
                ),
                tags=["discount"],
            )

        if topic == "marketplace":
            return SupportReply(
                topic=topic,
                reply=(
                    "Yes, Rootellect is available on Amazon India - just search \"Rootellect\". You can also order "
                    "directly at https://www.rootellect.com for COD and order updates on WhatsApp."
                ),
                tags=["marketplace"],
            )

        # results_timeline
        return SupportReply(
            topic=topic,
            reply=(
                "Botanical formulas work gradually - most people take them consistently for 6-8 weeks as part of a "
                "healthy routine. Results may vary from person to person. Tell me your main concern and I'll "
                "suggest the closest fit."
            ),
            tags=["results_timeline"],
        )

    def _keyword_reply(self, text: str, matched_campaigns: list[Campaign]) -> SupportReply | None:
        """Campaign keyword in a DM (e.g. "price", "link", "stress") → that campaign's DM + link."""
        lowered = text.lower()
        for campaign in matched_campaigns:
            keyword = self.matcher.matched_keyword(campaign, lowered)
            if not keyword or not campaign.dm_enabled:
                continue
            from app.services.campaign_conversion import CampaignConversionService

            link = campaign.product_link or ""
            body = CampaignConversionService().preview(campaign, text).dm_reply.strip()
            if not body:
                product = ROOTELLECT_PRODUCT_CATALOG.get(campaign.product_name or "")
                name = campaign.product_name or (product.name if product else "this formula")
                body = f"Here are the details for {name} 🌿"
            if link and link not in body:
                body = f"{body} {link}"
            whatsapp = campaign.whatsapp_link or self.settings.rootellect_whatsapp_link
            if campaign.whatsapp_followup_enabled and whatsapp and whatsapp not in body:
                body = f"{body}\nQuestions? WhatsApp us: {whatsapp}"
            return SupportReply(
                topic="campaign_keyword",
                reply=body,
                matched_keyword=keyword,
                campaign_id=campaign.id,
                tags=["campaign_keyword"],
            )
        return None
