import pytest

from app.models.entities import Campaign, Order
from app.services.campaign_matcher import instagram_shortcode
from app.services.instagram_support import InstagramSupportRouter, classify_topic


class FakeSession:
    def __init__(self, order=None):
        self.order = order

    async def scalar(self, _query):
        return self.order


@pytest.mark.parametrize(
    "text,topic",
    [
        ("where is my order??", "order_status"),
        ("mera order kab aayega", "order_status"),
        ("I want a refund", "refund_return"),
        ("product arrived damaged", "damaged_wrong"),
        ("payment failed but amount deducted", "payment"),
        ("I got a rash after taking it", "side_effect"),
        ("is cod available", "cod"),
        ("any coupon code?", "discount"),
        ("is it on amazon", "marketplace"),
        ("how to take mind calm", "how_to_use"),
        ("I want to talk to customer care", "human"),
        ("I love your reels", None),
        ("decode this", None),
    ],
)
def test_classify_topic(text, topic):
    assert classify_topic(text) == topic


@pytest.mark.parametrize(
    "url,code",
    [
        ("https://www.instagram.com/reels/DZXiLF2zBDh/", "DZXiLF2zBDh"),
        ("https://www.instagram.com/reel/DZXiLF2zBDh/?igsh=abc", "DZXiLF2zBDh"),
        ("https://www.instagram.com/p/ABC123/", "ABC123"),
        ("https://www.instagram.com/rootellect/reel/XYZ_9-a/", "XYZ_9-a"),
        ("https://www.rootellect.com", None),
    ],
)
def test_instagram_shortcode_accepts_reels_links(url, code):
    assert instagram_shortcode(url) == code


@pytest.mark.asyncio
async def test_order_status_without_order_asks_for_number():
    reply = await InstagramSupportRouter().handle(FakeSession(), "where is my order", None, [])
    assert reply.topic == "order_status"
    assert "order number" in reply.reply
    assert not reply.needs_human


@pytest.mark.asyncio
async def test_order_lookup_returns_status_and_tracking():
    order = Order(external_order_id="RT-10482", status="shipped", metadata_json={"track_code": "RT-10482"})
    reply = await InstagramSupportRouter().handle(
        FakeSession(order), "my phone number is 9876543210", None, [], last_outbound="Please share your order number"
    )
    assert reply.topic == "order_status"
    assert "RT-10482" in reply.reply and "shipped" in reply.reply
    assert "/track-order/RT-10482" in reply.reply


@pytest.mark.asyncio
async def test_issues_are_flagged_for_the_team():
    reply = await InstagramSupportRouter().handle(FakeSession(), "RT-10482 came damaged", None, [])
    assert reply.topic == "damaged_wrong"
    assert reply.needs_human
    assert "wa.me/918679008311" in reply.reply


@pytest.mark.asyncio
async def test_campaign_keyword_in_dm_sends_campaign_link():
    campaign = Campaign(
        id="c1",
        name="Mind Calm",
        status="active",
        product_name="Mind Calm",
        product_link="https://www.rootellect.com/products/mind-calm",
        keyword_triggers=["stress", "price"],
        dm_template="",
        public_reply_template="Sent you the details in DM.",
        public_reply_enabled=True,
        platform="both",
        dm_enabled=True,
        whatsapp_followup_enabled=True,
        whatsapp_link="https://wa.me/918679008311",
        metadata_json={},
    )
    # A generic keyword alone is not enough to pick a product...
    assert await InstagramSupportRouter().handle(FakeSession(), "price please", None, [campaign]) is None
    # ...but it is once the message names the product.
    reply = await InstagramSupportRouter().handle(FakeSession(), "price for mind calm?", None, [campaign])
    assert reply.topic == "campaign_keyword"
    assert reply.matched_keyword == "price"
    assert "rootellect.com/products/mind-calm" in reply.reply
    assert reply.campaign_id == "c1"


@pytest.mark.asyncio
async def test_unrecognised_message_falls_through_to_ai():
    assert await InstagramSupportRouter().handle(FakeSession(), "hello there", None, []) is None


@pytest.mark.asyncio
async def test_specific_keyword_in_dm_matches_campaign():
    campaign = Campaign(
        id="c2", name="PCOS", status="active", product_name="PCOS Support",
        product_link="https://www.rootellect.com/products/pcos-pcod-support",
        keyword_triggers=["pcos", "price"], dm_template="", public_reply_template="Sent you the details in DM.",
        public_reply_enabled=True, platform="both", dm_enabled=True, whatsapp_followup_enabled=False, metadata_json={},
    )
    reply = await InstagramSupportRouter().handle(FakeSession(), "PCOS", None, [campaign])
    assert reply.matched_keyword == "pcos"
    assert "pcos-pcod-support" in reply.reply
