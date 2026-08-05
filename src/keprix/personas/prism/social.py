"""Social media strategy and scheduling for PRISM."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from keprix.compat import UTC
from typing import Any

from keprix.personas.prism.persona import PRISM_PERSONA

PLATFORM_SCHEDULES: dict[str, dict[str, Any]] = {
    "linkedin": {
        "label": "LinkedIn",
        "best_days": ("Tuesday", "Wednesday", "Thursday"),
        "best_times_utc": ("08:00", "12:00", "17:00"),
        "content_types": ("thought leadership", "case study", "carousel", "poll"),
        "hashtag_count": (3, 5),
        "max_length": 3000,
    },
    "twitter": {
        "label": "X (Twitter)",
        "best_days": ("Monday", "Wednesday", "Friday"),
        "best_times_utc": ("09:00", "13:00", "18:00"),
        "content_types": ("thread", "tip", "stat", "question"),
        "hashtag_count": (1, 2),
        "max_length": 280,
    },
    "instagram": {
        "label": "Instagram",
        "best_days": ("Tuesday", "Thursday", "Saturday"),
        "best_times_utc": ("11:00", "14:00", "19:00"),
        "content_types": ("reel", "carousel", "story", "infographic"),
        "hashtag_count": (8, 15),
        "max_length": 2200,
    },
    "facebook": {
        "label": "Facebook",
        "best_days": ("Wednesday", "Thursday", "Sunday"),
        "best_times_utc": ("10:00", "15:00", "20:00"),
        "content_types": ("community post", "video", "event", "link share"),
        "hashtag_count": (1, 3),
        "max_length": 5000,
    },
    "tiktok": {
        "label": "TikTok",
        "best_days": ("Tuesday", "Thursday", "Friday"),
        "best_times_utc": ("12:00", "16:00", "21:00"),
        "content_types": ("short tutorial", "behind the scenes", "trend hook", "demo"),
        "hashtag_count": (3, 6),
        "max_length": 4000,
    },
}

DEFAULT_PLATFORMS = ("linkedin", "twitter", "instagram")


@dataclass(slots=True)
class SocialPost:
    day_offset: int
    scheduled_at: str
    platform: str
    content_type: str
    hook: str
    body: str
    hashtags: list[str]
    best_time_utc: str
    engagement_tactic: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "day_offset": self.day_offset,
            "scheduled_at": self.scheduled_at,
            "platform": self.platform,
            "content_type": self.content_type,
            "hook": self.hook,
            "body": self.body,
            "hashtags": list(self.hashtags),
            "best_time_utc": self.best_time_utc,
            "engagement_tactic": self.engagement_tactic,
        }


@dataclass
class SocialCalendar:
    calendar_id: str
    topic: str
    platforms: list[str]
    duration_days: int
    posts: list[SocialPost] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "calendar_id": self.calendar_id,
            "topic": self.topic,
            "platforms": list(self.platforms),
            "duration_days": self.duration_days,
            "posts": [post.to_dict() for post in self.posts],
            "summary": self.summary,
        }


def _slug_hashtags(topic: str, count: int) -> list[str]:
    tokens = [token for token in topic.lower().split() if token.isalnum()]
    base = [f"#{token}" for token in tokens[:3]]
    extras = [f"#{token}tips" for token in tokens[:2]]
    tags = base + extras
    while len(tags) < count:
        tags.append(f"#growth{len(tags) + 1}")
    return tags[:count]


class PrismSocial:
    def __init__(self, *, workspace_id: str = "default") -> None:
        self.workspace_id = workspace_id
        self.persona = PRISM_PERSONA

    def supported_platforms(self) -> list[str]:
        return sorted(PLATFORM_SCHEDULES)

    def build_calendar(
        self,
        *,
        topic: str,
        platforms: list[str] | None = None,
        duration_days: int = 14,
        start_date: datetime | None = None,
    ) -> SocialCalendar:
        from uuid import uuid4

        selected = [platform.lower() for platform in (platforms or list(DEFAULT_PLATFORMS))]
        selected = [platform for platform in selected if platform in PLATFORM_SCHEDULES]
        if not selected:
            selected = list(DEFAULT_PLATFORMS)

        start = start_date or datetime.now(UTC)
        posts: list[SocialPost] = []
        day = 0
        platform_index = 0

        while day < duration_days:
            platform = selected[platform_index % len(selected)]
            schedule = PLATFORM_SCHEDULES[platform]
            best_time = schedule["best_times_utc"][day % len(schedule["best_times_utc"])]
            scheduled = start + timedelta(days=day)
            scheduled_at = f"{scheduled.date().isoformat()}T{best_time}:00Z"
            content_type = schedule["content_types"][day % len(schedule["content_types"])]
            min_tags, max_tags = schedule["hashtag_count"]
            tag_count = min_tags + (day % (max_tags - min_tags + 1))
            hashtags = _slug_hashtags(topic, tag_count)

            hook = f"{topic}: {content_type.replace('_', ' ')} insight for day {day + 1}"
            body = (
                f"Share a concrete takeaway about {topic}. "
                f"Format: {content_type}. Ask one question to drive comments."
            )
            tactic = "Reply to first 5 comments within 2 hours" if platform in {"instagram", "twitter"} else "Tag a partner or customer example"

            posts.append(
                SocialPost(
                    day_offset=day,
                    scheduled_at=scheduled_at,
                    platform=platform,
                    content_type=content_type,
                    hook=hook,
                    body=body,
                    hashtags=hashtags,
                    best_time_utc=best_time,
                    engagement_tactic=tactic,
                )
            )
            day += 1
            platform_index += 1

        summary = (
            f"{len(posts)} posts across {', '.join(selected)} for '{topic}' "
            f"over {duration_days} days with platform-specific timing."
        )
        return SocialCalendar(
            calendar_id=str(uuid4()),
            topic=topic,
            platforms=selected,
            duration_days=duration_days,
            posts=posts,
            summary=summary,
        )
