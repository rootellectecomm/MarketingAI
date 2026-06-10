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
    assert decision.selected_product == "Mind Calm"
    assert decision.user_intent == "stress_sleep"
    assert decision.used_knowledge_source == "knowledge_base"


@pytest.mark.asyncio
async def test_fallback_ai_escalates_medical_claims():
    client = OpenAIDecisionClient()
    decision, _, _ = await client.generate_decision(AIRequestContext(text="Can this cure PCOS?"))

    assert decision.intent == "medical_risk"
    assert decision.send_decision == SendDecision.escalate
    assert "medical_risk" in decision.safety_flags


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("text", "product", "intent", "link"),
    [
        ("mind bahut active rehta hai night me", "Mind Calm", "stress_sleep", "/products/mind-calm"),
        ("pcos hai acne bhi hai", "PCOS Support", "pcos_pcod", "/products/pcos-pcod-support"),
        ("periods ke time fatigue hota hai", "Women Balance", "pms_energy", "/products/women-balance"),
        ("mom ko hot flashes hai", "Perimenopause Support", "perimenopause", "/products/perimenopause-support"),
    ],
)
async def test_fallback_ai_routes_rootellect_products(text: str, product: str, intent: str, link: str):
    client = OpenAIDecisionClient()
    decision, _, _ = await client.generate_decision(AIRequestContext(text=text, channel="whatsapp_message"))

    assert decision.selected_product == product
    assert decision.user_intent == intent
    assert decision.reply_channel == "whatsapp_message"
    assert decision.used_knowledge_source == "structured_product_catalog"
    assert link in decision.private_dm
    assert len(decision.private_dm.split()) <= 70
    assert decision.private_dm.count("?") <= 1


@pytest.mark.asyncio
async def test_fallback_ai_greets_with_one_question():
    client = OpenAIDecisionClient()
    decision, _, _ = await client.generate_decision(AIRequestContext(text="hello", channel="instagram_dm"))

    assert decision.selected_product is None
    assert decision.user_intent == "unclear"
    assert decision.private_dm == (
        "Hi - tell me your main concern in one line: sleep/stress, periods/PMS, PCOS, or 35+ hormonal changes?"
    )
    assert decision.private_dm.count("?") == 1


@pytest.mark.asyncio
async def test_fallback_ai_explains_rootellect_shortly():
    client = OpenAIDecisionClient()
    decision, _, _ = await client.generate_decision(AIRequestContext(text="what is rootellect"))

    assert decision.user_intent == "brand_question"
    assert decision.selected_product is None
    assert "clean vegan wellness brand" in decision.private_dm
    assert decision.private_dm.count("?") == 0
