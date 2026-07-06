"""Tests for PRISM social module."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from keprix.personas.prism.social import PLATFORM_SCHEDULES, PrismSocial


@pytest.fixture
def social() -> PrismSocial:
    return PrismSocial(workspace_id="ws-prism")


def test_supported_platforms_lists_known_networks(social: PrismSocial) -> None:
    platforms = social.supported_platforms()
    assert "linkedin" in platforms
    assert "instagram" in platforms
    assert "tiktok" in platforms


def test_build_calendar_is_platform_specific(social: PrismSocial) -> None:
    calendar = social.build_calendar(
        topic="organic growth",
        platforms=["linkedin", "twitter"],
        duration_days=4,
        start_date=datetime(2026, 1, 6, tzinfo=UTC),
    )
    assert calendar.duration_days == 4
    assert len(calendar.posts) == 4
    platforms_used = {post.platform for post in calendar.posts}
    assert platforms_used <= {"linkedin", "twitter"}

    for post in calendar.posts:
        schedule = PLATFORM_SCHEDULES[post.platform]
        assert post.best_time_utc in schedule["best_times_utc"]
        min_tags, max_tags = schedule["hashtag_count"]
        assert min_tags <= len(post.hashtags) <= max_tags
        assert post.content_type in schedule["content_types"]
        assert post.engagement_tactic


def test_calendar_summary_mentions_topic_and_platforms(social: PrismSocial) -> None:
    calendar = social.build_calendar(topic="local seo", platforms=["instagram"], duration_days=3)
    assert "local seo" in calendar.summary
    assert "instagram" in calendar.summary
