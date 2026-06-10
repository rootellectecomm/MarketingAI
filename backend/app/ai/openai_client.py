from __future__ import annotations

import json
import re
import time
from typing import Any

from app.ai.product_knowledge import CURE_CLAIM_TERMS, RED_FLAG_TERMS, knowledge_source, route_product
from app.ai.prompting import build_decision_prompt
from app.core.config import get_settings
from app.models.enums import ModerationAction, SendDecision
from app.schemas.ai import AIDecision, AIRequestContext


class OpenAIDecisionClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def generate_decision(self, context: AIRequestContext) -> tuple[AIDecision, int, dict[str, Any]]:
        started = time.perf_counter()
        prompt = build_decision_prompt(context)
        ai_input = {"mode": "openai", "prompt": prompt}

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
                            "You are Rootellect's premium wellness advisor. Return only the requested "
                            "structured JSON decision. Keep WhatsApp and DM replies under 70 words, ask "
                            "at most one question, avoid disease-cure claims, and include product links "
                            "when recommending a product."
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
            decision = self._apply_metadata_and_reply_rules(context, decision)
        except Exception as exc:
            ai_input["mode"] = "fallback_after_openai_error"
            decision = self._fallback_decision(context).model_copy(
                update={
                    "send_decision": SendDecision.queue_for_review,
                    "escalation_reason": f"OpenAI unavailable or invalid output: {exc}",
                    "confidence": 0.45,
                }
            )

        latency_ms = int((time.perf_counter() - started) * 1000)
        return decision, latency_ms, ai_input

    def _fallback_decision(self, context: AIRequestContext) -> AIDecision:
        text = context.text.strip()
        lowered = text.lower()
        retrieved_sources = [item.source for item in context.retrieved_context if item.source]
        source = knowledge_source(retrieved_sources)
        selected_product = route_product(text)
        purchase_intent = self._purchase_intent(lowered)

        if self._has_medical_risk(lowered):
            product_names = [selected_product.name] if selected_product else []
            reply = (
                "Rootellect can support general wellness guidance, but for medical symptoms, pregnancy, "
                "medication or treatment decisions, it's best to speak with a qualified professional."
            )
            return AIDecision(
                intent="medical_risk",
                sentiment="neutral",
                urgency="medium",
                purchase_intent=0.1,
                recommended_products=product_names,
                confidence=0.62,
                safety_flags=["medical_risk"],
                moderation_action=ModerationAction.escalate,
                public_reply="DMing a safe, general note.",
                private_dm=reply,
                selected_product=selected_product.name if selected_product else None,
                user_intent=selected_product.intent_key if selected_product else "medical_risk",
                reply_channel=context.channel,
                used_knowledge_source=source,
                lead_score_delta=0,
                escalation_reason="Medical-risk language detected.",
                send_decision=SendDecision.escalate,
            )

        intent = self._intent(lowered, purchase_intent)
        if intent == "brand_question":
            reply = (
                "Rootellect is a clean vegan wellness brand focused on calm, sleep, women's hormonal wellness, "
                "PCOS/PCOD support and perimenopause support. Tell me your main concern in one line and I'll "
                "suggest the closest product."
            )
            return self._decision(
                context=context,
                intent="general",
                user_intent="brand_question",
                selected_product=None,
                reply=reply,
                purchase_intent=0.25,
                confidence=0.78,
                source=source,
            )

        if not selected_product:
            reply = self._unclear_reply(lowered)
            schema_intent = intent if intent in {"shipping_question", "refund_question"} else "general"
            return self._decision(
                context=context,
                intent=schema_intent,
                user_intent="unclear",
                selected_product=None,
                reply=reply,
                purchase_intent=purchase_intent,
                confidence=0.7,
                source=source,
            )

        reply = self._product_reply(text, lowered, selected_product)
        return self._decision(
            context=context,
            intent="purchase_intent" if purchase_intent > 0.7 else "product_question",
            user_intent=selected_product.intent_key,
            selected_product=selected_product.name,
            reply=reply,
            purchase_intent=purchase_intent,
            confidence=0.86 if context.retrieved_context else 0.78,
            source=source,
        )

    def _decision(
        self,
        *,
        context: AIRequestContext,
        intent: str,
        user_intent: str,
        selected_product: str | None,
        reply: str,
        purchase_intent: float,
        confidence: float,
        source: str,
    ) -> AIDecision:
        send_decision = (
            SendDecision.send if confidence >= self.settings.ai_min_autosend_confidence else SendDecision.queue_for_review
        )
        public_reply = "" if not context.allow_public_reply else self._public_reply(selected_product)
        private_dm = reply if context.allow_dm or context.channel == "whatsapp_message" else ""
        return AIDecision(
            intent=intent,
            sentiment="positive" if self._positive(context.text.lower()) else "neutral",
            urgency="medium" if purchase_intent > 0.7 else "low",
            purchase_intent=purchase_intent,
            recommended_products=[selected_product] if selected_product else [],
            confidence=confidence,
            safety_flags=[],
            moderation_action=ModerationAction.allow,
            public_reply=public_reply,
            private_dm=private_dm,
            whatsapp_followup=None,
            selected_product=selected_product,
            user_intent=user_intent,
            reply_channel=context.channel,
            used_knowledge_source=source,
            lead_score_delta=20 if purchase_intent > 0.7 else 8,
            escalation_reason=None if send_decision == SendDecision.send else "Confidence below autosend threshold.",
            send_decision=send_decision,
        )

    def _apply_metadata_and_reply_rules(self, context: AIRequestContext, decision: AIDecision) -> AIDecision:
        selected_product = decision.selected_product
        if not selected_product and decision.recommended_products:
            selected_product = decision.recommended_products[0]
        routed_product = route_product(context.text)
        if not selected_product and routed_product:
            selected_product = routed_product.name
        user_intent = decision.user_intent
        if user_intent == "general" and routed_product:
            user_intent = routed_product.intent_key
        source = decision.used_knowledge_source
        if source == "none":
            source = knowledge_source([item.source for item in context.retrieved_context if item.source])

        return decision.model_copy(
            update={
                "selected_product": selected_product,
                "user_intent": user_intent,
                "reply_channel": context.channel,
                "used_knowledge_source": source,
                "recommended_products": [selected_product] if selected_product else decision.recommended_products[:1],
                "private_dm": self._limit_questions(decision.private_dm),
                "public_reply": self._limit_questions(decision.public_reply),
                "whatsapp_followup": self._limit_questions(decision.whatsapp_followup or "")
                if decision.whatsapp_followup
                else None,
            }
        )

    @staticmethod
    def _purchase_intent(text: str) -> float:
        words = set(re.findall(r"[a-z0-9+]+", text))
        purchase_words = {"price", "buy", "link", "order", "cost", "available", "dm"}
        return 0.8 if purchase_words.intersection(words) else 0.35

    @staticmethod
    def _has_medical_risk(text: str) -> bool:
        has_red_flag = any(term in text for term in RED_FLAG_TERMS)
        asks_cure = any(term in text for term in CURE_CLAIM_TERMS)
        medical_context = any(term in text for term in ("pcos", "pcod", "anxiety", "insomnia", "thyroid", "diabetes"))
        return has_red_flag or (asks_cure and medical_context)

    @staticmethod
    def _positive(text: str) -> bool:
        return any(word in text for word in ("love", "good", "best", "great"))

    @staticmethod
    def _intent(text: str, purchase_intent: float) -> str:
        if "what is rootellect" in text or "about rootellect" in text:
            return "brand_question"
        if "shipping" in text:
            return "shipping_question"
        if "refund" in text or "return" in text:
            return "refund_question"
        if purchase_intent > 0.7:
            return "purchase_intent"
        return "product_question"

    @staticmethod
    def _unclear_reply(text: str) -> str:
        if text in {"hello", "hi", "hey", "hii", "helo"}:
            return (
                "Hi - tell me your main concern in one line: sleep/stress, periods/PMS, PCOS, "
                "or 35+ hormonal changes?"
            )
        return "I don't want to guess. Can you tell me your main concern in one line?"

    @staticmethod
    def _public_reply(selected_product: str | None) -> str:
        if selected_product:
            return "DMing the closest fit."
        return "DMing you a quick question."

    @staticmethod
    def _product_reply(text: str, lowered: str, product) -> str:
        link_requested = any(word in lowered for word in ("link", "price", "buy", "order", "cost"))
        if product.name == "Mind Calm":
            if link_requested:
                return (
                    f"Here's Mind Calm: {product.url} - best if your concern is stress, overthinking or sleep quality."
                )
            if "wake" in lowered or "tired" in lowered:
                return (
                    "This can happen when sleep isn't mentally restorative. If stress, late-night thoughts or brain "
                    f"fatigue are involved, Mind Calm fits better. It supports calmness, sleep quality and next-day "
                    f"clarity. {product.url}"
                )
            return (
                "Got it. This sounds more like overthinking + sleep quality support. Mind Calm is the closest fit - "
                f"it's non-melatonin and designed to support calmness, relaxation and better sleep quality. {product.url}"
            )
        if product.name == "Women Balance":
            return (
                "This sounds more like PMS + energy support. Women Balance fits better - it supports daily women's "
                f"hormonal wellness, mood and energy with Shatavari, Moringa, KSM-66 Ashwagandha, iron and vegan D3. "
                f"{product.url}"
            )
        if product.name == "PCOS Support":
            return (
                "For PCOS + acne linked with hormonal imbalance, PCOS Support is the most relevant option. It's a "
                f"non-hormonal formula designed to support cycle wellness, hormonal balance, skin concerns and "
                f"metabolic health. {product.url}"
            )
        if product.name == "Perimenopause Support":
            return (
                "If she's around 35+ or in the transition phase, Perimenopause Support is the closest fit. It's designed "
                f"to support hot flashes, mood, sleep and hormonal transition comfort. {product.url}"
            )
        return f"For this, the closest Rootellect option is {product.name}. {product.url}"

    @staticmethod
    def _limit_questions(reply: str) -> str:
        if reply.count("?") <= 1:
            return reply
        first_question = reply.find("?")
        return reply[: first_question + 1]
