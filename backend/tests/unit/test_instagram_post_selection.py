from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app import models  # noqa: F401
from app.api.v1.routes.instagram_posts import campaign_targets_post, set_post_target
from app.database.base import Base
from app.models.entities import Campaign
from app.services.campaign_matcher import CampaignMatcher

REEL = "https://www.instagram.com/reel/DAbc123xyz/"
OTHER = "https://www.instagram.com/p/OTHER999/"


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as db:
        yield db
    await engine.dispose()


def campaign(name: str, keywords: list[str] | None = None, metadata: dict | None = None) -> Campaign:
    return Campaign(
        name=name,
        status="active",
        platform="both",
        keyword_triggers=keywords or [],
        metadata_json=metadata or {},
        public_reply_enabled=True,
        dm_enabled=True,
    )


async def test_untargeted_campaign_does_not_answer_comments_in_selected_mode(session):
    session.add(campaign("Everywhere", ["price"]))
    await session.flush()
    matcher = CampaignMatcher()
    assert await matcher.match_active(session, "price?", media_id="1", media_permalink=OTHER)  # old behaviour
    assert await matcher.match_active(
        session, "price?", media_id="1", media_permalink=OTHER, require_media_target=True
    ) == []


async def test_selected_post_is_answered_and_other_posts_are_not(session):
    selected = campaign("Mind Calm reel")
    set_post_target(selected, "1789", REEL, True)
    session.add(selected)
    await session.flush()
    matcher = CampaignMatcher()
    hit = await matcher.match_active(session, "how to buy", media_id="1789", media_permalink=REEL, require_media_target=True)
    assert [c.name for c in hit] == ["Mind Calm reel"]
    miss = await matcher.match_active(session, "how to buy", media_id="555", media_permalink=OTHER, require_media_target=True)
    assert miss == []


def test_set_post_target_toggles_cleanly():
    c = campaign("Toggle", metadata={"target_media_urls": [OTHER], "target_media_ids": ["555"]})
    set_post_target(c, "1789", REEL, True)
    assert campaign_targets_post(c, "1789", REEL)
    assert campaign_targets_post(c, "555", OTHER)
    set_post_target(c, "1789", REEL, True)  # idempotent
    assert c.metadata_json["target_media_ids"].count("1789") == 1
    set_post_target(c, "1789", REEL, False)
    assert not campaign_targets_post(c, "1789", REEL)
    assert campaign_targets_post(c, "555", OTHER)
