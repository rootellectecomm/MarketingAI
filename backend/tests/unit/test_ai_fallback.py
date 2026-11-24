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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "text",
    [
        "Hello",
        "Hi Rootellect! I'd like to know more about your wellness products and find out which one is right for me.",
        "Hi which prodcut help me with stress",
    ],
)
async def test_whatsapp_greetings_and_questions_get_a_reply(text: str):
    client = OpenAIDecisionClient()
    client.settings = client.settings.model_copy(update={"openai_api_key": None})
    decision, _, _ = await client.generate_decision(AIRequestContext(text=text, channel="whatsapp_message"))
    assert decision.send_decision == SendDecision.send
    assert decision.private_dm


@pytest.mark.asyncio
async def test_whatsapp_never_autosends_medical_escalations():
    client = OpenAIDecisionClient()
    client.settings = client.settings.model_copy(update={"openai_api_key": None})
    decision, _, _ = await client.generate_decision(
        AIRequestContext(text="Will this cure my PCOS permanently?", channel="whatsapp_message")
    )
    assert decision.send_decision != SendDecision.send


@pytest.mark.asyncio
async def test_openai_error_falls_back_to_curated_reply_instead_of_silence(monkeypatch):
    client = OpenAIDecisionClient()
    client.settings = client.settings.model_copy(update={"openai_api_key": "sk-test"})

    class Boom:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("network down")

    import openai

    monkeypatch.setattr(openai, "AsyncOpenAI", Boom)
    decision, _, ai_input = await client.generate_decision(
        AIRequestContext(text="Hi which product helps with stress", channel="whatsapp_message")
    )
    assert ai_input["mode"] == "fallback_after_openai_error"
    assert decision.send_decision == SendDecision.send and "Mind Calm" in decision.private_dm


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "text,product",
    [
        ("i want strees supplement", "Mind Calm"),
        ("bahut tension rehti hai", "Mind Calm"),
        ("1", "Mind Calm"),
        ("3", "PCOS Support"),
        ("something for my mood swings", "Women Balance"),
    ],
)
async def test_whatsapp_typos_hinglish_and_menu_numbers_route_to_a_product(text: str, product: str):
    client = OpenAIDecisionClient()
    client.settings = client.settings.model_copy(update={"openai_api_key": None})
    decision, _, _ = await client.generate_decision(AIRequestContext(text=text, channel="whatsapp_message"))
    assert decision.selected_product == product
    assert decision.send_decision == SendDecision.send


@pytest.mark.asyncio
async def test_unclear_message_gets_menu_then_human_handoff_not_a_loop():
    from app.schemas.ai import ThreadMessage

    client = OpenAIDecisionClient()
    client.settings = client.settings.model_copy(update={"openai_api_key": None})
    first, _, _ = await client.generate_decision(
        AIRequestContext(text="i want some prodcut for me which best suits me", channel="whatsapp_message")
    )
    assert "Reply with 1-4" in first.private_dm and first.send_decision == SendDecision.send
    second, _, _ = await client.generate_decision(
        AIRequestContext(
            text="not sure",
            channel="whatsapp_message",
            thread_history=[ThreadMessage(direction="outbound", body=first.private_dm, channel="whatsapp")],
        )
    )
    assert "wellness team" in second.private_dm and "Reply with 1-4" not in second.private_dm
    assert second.escalation_reason
