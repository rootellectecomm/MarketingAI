from __future__ import annotations

import json
import time
from typing import Any

from app.ai.prompting import build_decision_prompt
from app.core.config import get_settings
from app.models.enums import ModerationAction, SendDecision
from app.schemas.ai import ROOTELLECT_PRODUCTS, AIDecision, AIRequestContext


class OpenAIDecisionClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def generate_decision(self, context: AIRequestContext) -> tuple[AIDecision, int, dict[str, Any]]:
        started = time.perf_counter()
        prompt = build_decision_prompt(context)

        if not self.settings.openai_api_key:
            decision = self._fallback_decision(context)
            latency_ms = int((time.perf_counter() - started) * 1000)
            return decision, latency_ms, {"mode": "fallback", "prompt": prompt}

        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self.settings.openai_api_key)
            response = await client.responses.parse(
                model=self.settings.openai_model,
                input=[
                    {
                        "role": "system",
                        "content": (
                            "You are Rootellect's safe, premium wellness automation engine. "
                            "Return only the requested structured JSON decision."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                text_format=AIDecision,
            )
            parsed = getattr(response, "output_parsed", None)
            if isinstance(parsed, AIDecision):
                decision = parsed
            elif isinstance(parsed, dict):
                decision = AIDecision.model_validate(parsed)
            else:
                decision = AIDecision.model_validate(json.loads(response.output_text or "{}"))
        except Exception as exc:
            decision = self._fallback_decision(context).model_copy(
                update={
                    "send_decision": SendDecision.queue_for_review,
                    "escalation_reason": f"OpenAI unavailable or invalid output: {exc}",
                    "confidence": 0.45,
                }
            )

        latency_ms = int((time.perf_counter() - started) * 1000)
        return decision, latency_ms, {"mode": "openai", "prompt": prompt}

    def _fallback_decision(self, context: AIRequestContext) -> AIDecision:
        text = context.text.lower()
        products = [product for product in ROOTELLECT_PRODUCTS if product.lower() in text]
        if not products:
            keyword_map = {
                "pcos": "PCOS Support",
                "calm": "Mind Calm",
                "stress": "Mind Calm",
                "sleep": "Mind Calm",
                "menopause": "Menopause Prime Support",
                "bone": "Menopause Bone & Joint Support",
                "joint": "Menopause Bone & Joint Support",
                "vitamin": "Women Multivitamin 18+",
                "d3": "D3 & Calcium",
                "calcium": "D3 & Calcium",
                "workout": "Preworkout",
                "acv": "ACV Moringa",
                "moringa": "ACV Moringa",
            }
            products = [product for keyword, product in keyword_map.items() if keyword in text]

        purchase_words = {"price", "buy", "link", "order", "cost", "available", "dm"}
        purchase_intent = 0.75 if purchase_words.intersection(text.split()) else 0.25
        intent = "purchase_intent" if purchase_intent > 0.7 else "product_question"
        if "shipping" in text:
            intent = "shipping_question"
        if "refund" in text or "return" in text:
            intent = "refund_question"
        if any(word in text for word in ["cure", "diagnose", "pregnant", "medicine"]):
            return AIDecision(
                intent="medical_risk",
                sentiment="neutral",
                urgency="medium",
                purchase_intent=0.1,
                recommended_products=products[:2],
                confidence=0.62,
                safety_flags=["medical_risk"],
                moderation_action=ModerationAction.escalate,
                public_reply="Thanks for reaching out. We will help you with general product information in DM.",
                private_dm=(
                    "Thanks for sharing this. We can explain Rootellect products, but for any medical "
                    "condition, diagnosis, pregnancy, medication, or treatment advice, please consult a "
                    "qualified healthcare professional."
                ),
                lead_score_delta=0,
                escalation_reason="Medical-risk language detected.",
                send_decision=SendDecision.escalate,
            )

        product_text = products[0] if products else "the right Rootellect option"
        confidence = 0.82 if context.retrieved_context else 0.68
        send_decision = (
            SendDecision.send
            if confidence >= self.settings.ai_min_autosend_confidence
            else SendDecision.queue_for_review
        )
        return AIDecision(
            intent=intent,
            sentiment="positive" if any(word in text for word in ["love", "good", "best"]) else "neutral",
            urgency="medium" if purchase_intent > 0.7 else "low",
            purchase_intent=purchase_intent,
            recommended_products=products[:2],
            confidence=confidence,
            safety_flags=[],
            moderation_action=ModerationAction.allow,
            public_reply="Absolutely. Sending the details to your DM.",
            private_dm=(
                f"Hi! Thanks for your interest in {product_text}. Here is a quick overview from "
                "Rootellect. Tell us your wellness goal and we can guide you to the best fit."
            ),
            whatsapp_followup=None,
            lead_score_delta=20 if purchase_intent > 0.7 else 8,
            escalation_reason=None if send_decision == SendDecision.send else "Confidence below autosend threshold.",
            send_decision=send_decision,
        )
