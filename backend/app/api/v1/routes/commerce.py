from __future__ import annotations

import hashlib
import hmac
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.database.session import get_session
from app.models.entities import CartAbandonment, Lead, Order
from app.services.provider_factory import get_whatsapp_provider

router = APIRouter(prefix="/commerce", tags=["commerce"])


def _verify_shopify_hmac(raw_body: bytes, hmac_header: str | None, secret: str) -> bool:
    if not hmac_header or not secret:
        return False
    digest = hmac.new(secret.encode(), raw_body, hashlib.sha256).digest()
    import base64

    computed = base64.b64encode(digest).decode()
    return hmac.compare_digest(computed, hmac_header)


@router.post("/shopify/webhook")
async def shopify_webhook(request: Request, session: AsyncSession = Depends(get_session)) -> dict:
    settings = get_settings()
    raw_body = await request.body()
    signature = request.headers.get("x-shopify-hmac-sha256")
    if settings.environment == "production" and not _verify_shopify_hmac(
        raw_body, signature, settings.shopify_webhook_secret or ""
    ):
        raise HTTPException(status_code=401, detail="Invalid Shopify webhook signature")

    payload = json.loads(raw_body.decode() or "{}")
    topic = request.headers.get("x-shopify-topic", "")

    if topic in {"orders/create", "orders/paid"}:
        external_id = str(payload.get("id") or payload.get("order_number") or "")
        phone = (payload.get("phone") or (payload.get("customer") or {}).get("phone") or "").strip()
        email = (payload.get("email") or (payload.get("customer") or {}).get("email") or "").strip()
        lead = None
        if phone:
            lead = await session.scalar(select(Lead).where(Lead.phone == phone))
        order = await session.scalar(select(Order).where(Order.external_order_id == external_id))
        if not order:
            order = Order(
                external_order_id=external_id,
                lead_id=lead.id if lead else None,
                source="shopify",
                status="paid" if topic == "orders/paid" else "created",
                total_amount=float(payload.get("total_price") or 0),
                currency=payload.get("currency") or "INR",
                customer_email=email or None,
                customer_phone=phone or None,
                line_items=payload.get("line_items") or [],
                metadata_json={"topic": topic},
            )
            session.add(order)
        else:
            order.status = "paid"
            order.metadata_json = {**(order.metadata_json or {}), "topic": topic}

    if topic in {"checkouts/create", "carts/update"}:
        cart_id = str(payload.get("id") or payload.get("token") or "")
        phone = (payload.get("phone") or (payload.get("customer") or {}).get("phone") or "").strip()
        checkout_url = payload.get("abandoned_checkout_url") or payload.get("checkout_url")
        cart = await session.scalar(select(CartAbandonment).where(CartAbandonment.external_cart_id == cart_id))
        if not cart:
            lead = await session.scalar(select(Lead).where(Lead.phone == phone)) if phone else None
            cart = CartAbandonment(
                external_cart_id=cart_id,
                lead_id=lead.id if lead else None,
                source="shopify",
                status="abandoned",
                checkout_url=checkout_url,
                metadata_json={"topic": topic},
            )
            session.add(cart)
            await session.flush()

            if phone and checkout_url and not cart.recovery_sent_at:
                message = (
                    "Just checking if you needed help choosing. "
                    "Sometimes wellness decisions take time — happy to guide if you're confused."
                )
                provider = get_whatsapp_provider()
                lead = lead or await session.scalar(select(Lead).where(Lead.phone == phone))
                if lead and lead.whatsapp_opt_in:
                    result = await provider.send_whatsapp_text(phone, f"{message}\n{checkout_url}")
                else:
                    result = await provider.send_whatsapp_template(
                        phone,
                        settings.whatsapp_opt_in_template_name,
                        [message[:180]],
                    )
                if result.ok:
                    cart.recovery_sent_at = cart.updated_at

    await session.commit()
    return {"ok": True, "topic": topic}
