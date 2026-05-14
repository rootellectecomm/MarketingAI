import pytest

from app.ai.openai_client import OpenAIDecisionClient
from app.models.enums import SendDecision
from app.schemas.ai import AIRequestContext, RetrievedContext


@pytest.mark.asyncio
async def test_fallback_ai_sends_high_confidence_product_reply():
    client = OpenAIDecisionClient()
    decision, _, _ = await client.generate_decision(
        AIRequestContext(
            text="Need price for Mind Calm",
            username="riya",
            retrieved_context=[
                RetrievedContext(title="Mind Calm", category="product", content="Mind Calm supports everyday calm routines.")
            ],
        )
    )

    assert decision.intent == "purchase_intent"
    assert decision.send_decision == SendDecision.send
    assert "Mind Calm" in decision.recommended_products


@pytest.mark.asyncio
async def test_fallback_ai_escalates_medical_claims():
    client = OpenAIDecisionClient()
    decision, _, _ = await client.generate_decision(AIRequestContext(text="Can this cure PCOS?"))

    assert decision.intent == "medical_risk"
    assert decision.send_decision == SendDecision.escalate
    assert "medical_risk" in decision.safety_flags
