"""Approved WhatsApp templates used for Rootellect order notifications.

This module is the single source of truth for template copy. The same
definitions are used to submit templates to Meta
(``scripts/create_whatsapp_templates.py``) and to send them, so the variables
the sender fills always match what Meta approved.

Copy rules (WhatsApp + FSSAI):
- No health claims: "supports", never "treats/cures/fixes".
- Utility templates stay strictly about the customer's own order. No offers,
  discounts or product promotion, or Meta re-classifies them as Marketing.
- A body may not start or end with a variable, and needs enough fixed text
  around its variables.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Category = Literal["UTILITY", "MARKETING"]
Consent = Literal["transactional", "marketing"]


@dataclass(frozen=True, slots=True)
class TemplateButton:
    type: Literal["URL", "QUICK_REPLY"]
    text: str
    # URL buttons: fixed prefix, Meta appends the dynamic suffix ({{1}}).
    url_prefix: str | None = None
    example_suffix: str | None = None
    dynamic: bool = True


@dataclass(frozen=True, slots=True)
class WhatsAppTemplate:
    kind: str
    name: str
    category: Category
    consent: Consent
    body: str
    body_examples: tuple[str, ...]
    footer: str | None = None
    buttons: tuple[TemplateButton, ...] = field(default_factory=tuple)
    # Sent the moment the triggering event arrives, ignoring quiet hours.
    immediate: bool = False
    # Image header: default image (also the example Meta reviews). Products
    # templates swap in the customer's product image at send time.
    header_image: str | None = None
    # Previous approved version without the header. Used as a fallback while
    # Meta is still reviewing this version, so no customer message is lost.
    legacy_name: str | None = None


SITE = "https://www.rootellect.com"
IMG = f"{SITE}/whatsapp"
PRODUCT_IMAGE_SLUGS = ("mind-calm", "women-balance", "balance-pcos-pcod-support", "perimenopause-support")


def product_image(slug_or_title: str | None) -> str | None:
    """Header image for a product slug or title; ``None`` when no product image fits."""
    text = (slug_or_title or "").lower()
    if not text:
        return None
    if "pcos" in text or "pcod" in text:
        slug = "balance-pcos-pcod-support"
    elif "peri" in text or "menopause" in text:
        slug = "perimenopause-support"
    elif "mind" in text or "calm" in text:
        slug = "mind-calm"
    elif "women" in text and "balance" in text:
        slug = "women-balance"
    else:
        return None
    return f"{IMG}/product-{slug}.jpg"
STOP_FOOTER = "Reply STOP to opt out of WhatsApp updates"

TEMPLATES: dict[str, WhatsAppTemplate] = {
    template.kind: template
    for template in (
        WhatsAppTemplate(
            kind="order_confirmed",
            name="rootellect_order_confirmed_v2",
            legacy_name="rootellect_order_confirmed_v1",
            header_image=f"{IMG}/order-confirmed.jpg",
            category="UTILITY",
            consent="transactional",
            immediate=True,
            body=(
                "Hi {{1}}, thank you for choosing Rootellect.\n\n"
                "Your order *{{2}}* is confirmed. Order total: ₹{{3}}.\n\n"
                "We're packing it with care and will share your tracking details as soon as it ships."
            ),
            body_examples=("Ananya", "RT-10482", "1,299"),
            footer=STOP_FOOTER,
            buttons=(TemplateButton("URL", "Track order", url_prefix=f"{SITE}/track-order/", example_suffix="RT-10482"),),
        ),
        WhatsAppTemplate(
            kind="cod_order_confirm",
            # v2 was re-classified as Marketing by Meta (higher cost, blocked for
            # some users with error 131049). v3 is plain order wording, no header,
            # submitted as Utility on 24 Nov 2026. v1 has no header, so it is the
            # safe fallback while v3 is in review.
            name="rootellect_cod_order_confirm_v3",
            legacy_name="rootellect_cod_order_confirm_v1",
            header_image=None,
            category="UTILITY",
            consent="transactional",
            immediate=True,
            body=(
                "Hi {{1}}, we've received your Rootellect order *{{2}}* (Cash on Delivery). "
                "Amount payable on delivery: ₹{{3}}. "
                "Please confirm this order using the button below so we can dispatch it."
            ),
            body_examples=("Priya", "RT10245", "799"),
            footer=None,
            buttons=(
                TemplateButton("QUICK_REPLY", "Confirm order"),
                TemplateButton("QUICK_REPLY", "Cancel order"),
            ),
        ),
        WhatsAppTemplate(
            kind="order_shipped",
            name="rootellect_order_shipped_v2",
            legacy_name="rootellect_order_shipped_v1",
            header_image=f"{IMG}/order-shipped.jpg",
            category="UTILITY",
            consent="transactional",
            body=(
                "Good news, {{1}}! Your Rootellect order *{{2}}* has shipped with {{3}}.\n\n"
                "Tracking number: {{4}}. You can follow every step using the button below."
            ),
            body_examples=("Ananya", "RT-10482", "Delhivery", "1234567890123"),
            footer=STOP_FOOTER,
            buttons=(TemplateButton("URL", "Track order", url_prefix=f"{SITE}/track-order/", example_suffix="RT-10482"),),
        ),
        WhatsAppTemplate(
            kind="out_for_delivery",
            name="rootellect_out_for_delivery_v2",
            legacy_name="rootellect_out_for_delivery_v1",
            header_image=f"{IMG}/out-for-delivery.jpg",
            category="UTILITY",
            consent="transactional",
            body=(
                "Hi {{1}}, your Rootellect order *{{2}}* is out for delivery today.\n\n"
                "Amount to pay: {{3}}. Please keep your phone nearby so our courier partner can reach you."
            ),
            body_examples=("Ananya", "RT-10482", "₹0 (already paid)"),
            footer=STOP_FOOTER,
        ),
        WhatsAppTemplate(
            kind="order_delivered",
            name="rootellect_order_delivered_v2",
            legacy_name="rootellect_order_delivered_v1",
            header_image=f"{IMG}/order-delivered.jpg",
            category="UTILITY",
            consent="transactional",
            body=(
                "Hi {{1}}, your Rootellect order *{{2}}* has been delivered.\n\n"
                "If anything isn't right with your package, simply reply to this message and our team will help you."
            ),
            body_examples=("Ananya", "RT-10482"),
            footer=STOP_FOOTER,
        ),
        WhatsAppTemplate(
            kind="delivery_failed",
            name="rootellect_delivery_attempt_failed_v2",
            legacy_name="rootellect_delivery_attempt_failed_v1",
            header_image=f"{IMG}/delivery-update.jpg",
            category="UTILITY",
            consent="transactional",
            body=(
                "Hi {{1}}, our courier partner couldn't deliver your Rootellect order *{{2}}* today.\n\n"
                "Please reply with a convenient time or any address details we should know, and we'll help arrange redelivery."
            ),
            body_examples=("Ananya", "RT-10482"),
            footer=STOP_FOOTER,
        ),
        WhatsAppTemplate(
            kind="usage_guide",
            name="rootellect_usage_guide_v2",
            legacy_name="rootellect_usage_guide_v1",
            header_image=f"{IMG}/product-mind-calm.jpg",
            # Meta re-classified this as Marketing on review (2026-10-31), so it
            # may only go to customers who opted in to marketing messages.
            category="MARKETING",
            consent="marketing",
            body=(
                "Hi {{1}}, a quick note on getting started with your {{2}}.\n\n"
                "Take it daily as directed on the label, ideally at the same time each day, alongside a balanced routine. "
                "Consistency over a few weeks matters more than any single day.\n\n"
                "Questions about how to take it? Reply here and our team will help."
            ),
            body_examples=("Ananya", "Rootellect Mind Calm"),
            footer=STOP_FOOTER,
        ),
        WhatsAppTemplate(
            kind="review_request",
            name="rootellect_review_request_v2",
            legacy_name="rootellect_review_request_v1",
            header_image=f"{IMG}/review-request.jpg",
            category="UTILITY",
            consent="transactional",
            body=(
                "Hi {{1}}, it's been about two weeks since your {{2}} arrived.\n\n"
                "We'd value your honest feedback on your order. It takes a minute and helps others choose with confidence."
            ),
            body_examples=("Ananya", "Rootellect Mind Calm"),
            footer=STOP_FOOTER,
            buttons=(TemplateButton("URL", "Share feedback", url_prefix=f"{SITE}/review/", example_suffix="token123"),),
        ),
        WhatsAppTemplate(
            kind="reorder_reminder",
            name="rootellect_reorder_reminder_v2",
            legacy_name="rootellect_reorder_reminder_v1",
            header_image=f"{IMG}/product-mind-calm.jpg",
            category="MARKETING",
            consent="marketing",
            body=(
                "Hi {{1}}, your {{2}} supply may run out in about 5 days.\n\n"
                "Staying consistent is what matters most, so you can reorder in a few taps before you run low."
            ),
            body_examples=("Ananya", "Rootellect Mind Calm"),
            footer=STOP_FOOTER,
            buttons=(TemplateButton("URL", "Reorder", url_prefix=f"{SITE}/products/", example_suffix="mind-calm"),),
        ),
        WhatsAppTemplate(
            kind="welcome_offer",
            name="rootellect_welcome_offer_v2",
            legacy_name="rootellect_welcome_offer_v1",
            header_image=f"{IMG}/welcome.jpg",
            category="MARKETING",
            consent="marketing",
            body=(
                "Hi {{1}}, welcome to Rootellect 🌿\n\n"
                "Thank you for joining us. Enjoy {{2}}% off your first order with code *{{3}}*, valid until {{4}}.\n\n"
                "Our clean-label, vegan formulations are designed to support everyday balance. "
                "Not sure where to start? Reply here and we'll help you choose."
            ),
            body_examples=("Ananya", "10", "WELCOMEAB12CD34", "8 Dec 2026"),
            footer=STOP_FOOTER,
            buttons=(TemplateButton("URL", "Shop now", url_prefix=f"{SITE}/shop", dynamic=False),),
        ),
        WhatsAppTemplate(
            kind="checkout_reminder",
            name="rootellect_checkout_reminder_v2",
            legacy_name="rootellect_checkout_reminder_v1",
            header_image=f"{IMG}/product-mind-calm.jpg",
            category="MARKETING",
            consent="marketing",
            body=(
                "Hi {{1}}, you left {{2}} in your Rootellect cart.\n\n"
                "Your items are saved whenever you're ready. Not sure what suits you? Reply here and we'll help you choose."
            ),
            body_examples=("Ananya", "Rootellect Mind Calm"),
            footer=STOP_FOOTER,
            buttons=(TemplateButton("URL", "Complete order", url_prefix=f"{SITE}/cart", dynamic=False),),
        ),
        WhatsAppTemplate(
            kind="team_alert",
            # Sent to the Rootellect team's own phones (not customers) when a chat
            # needs a person and the team member has not messaged us in 24 hours.
            name="rootellect_team_alert_v1",
            category="UTILITY",
            consent="transactional",
            immediate=True,
            body=(
                "New customer request on Rootellect WhatsApp. Customer: {{1}} ({{2}}). "
                "Reason: {{3}}. Message: {{4}}. Please reply from the MarketingAI dashboard."
            ),
            body_examples=("Priya", "+91 98765 43210", "Asked to talk to a person", "Which product is right for stress?"),
        ),
    )
}


def get_template(kind: str) -> WhatsAppTemplate:
    return TEMPLATES[kind]


def meta_template_payload(template: WhatsAppTemplate, language: str, header_handle: str | None = None) -> dict:
    """Request body for POST /{WABA_ID}/message_templates.

    ``header_handle`` is the Resumable Upload handle of the example header image
    (required by Meta when the template has an image header).
    """
    components: list[dict] = []
    if template.header_image:
        if not header_handle:
            raise ValueError(f"{template.name} has an image header: upload its example image first")
        components.append({"type": "HEADER", "format": "IMAGE", "example": {"header_handle": [header_handle]}})
    components += [
        {"type": "BODY", "text": template.body, "example": {"body_text": [list(template.body_examples)]}},
    ]
    if template.footer:
        components.append({"type": "FOOTER", "text": template.footer})
    if template.buttons:
        buttons: list[dict] = []
        for button in template.buttons:
            if button.type == "QUICK_REPLY":
                buttons.append({"type": "QUICK_REPLY", "text": button.text})
            elif button.dynamic:
                buttons.append(
                    {
                        "type": "URL",
                        "text": button.text,
                        "url": f"{button.url_prefix}{{{{1}}}}",
                        "example": [f"{button.url_prefix}{button.example_suffix}"],
                    }
                )
            else:
                buttons.append({"type": "URL", "text": button.text, "url": button.url_prefix})
        components.append({"type": "BUTTONS", "buttons": buttons})
    return {"name": template.name, "language": language, "category": template.category, "components": components}
