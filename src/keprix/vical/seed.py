"""Default Consultation seed matching prior ECHO 09-17 weekdays."""

from __future__ import annotations

from keprix.vical.store import VicalStore, vical_store


DEFAULT_SLUG = "consultation"
DEFAULT_NAME = "Consultation"
DEFAULT_DURATION_MINUTES = 30
DEFAULT_TIMEZONE = "UTC"
# Match EchoScheduler BUSINESS_DAY_START_HOUR / END_HOUR
WEEKDAY_START = "09:00"
WEEKDAY_END = "17:00"


def ensure_default_consultation(
    user_id: str,
    *,
    store: VicalStore | None = None,
    workspace_id: str | None = None,
    timezone: str = DEFAULT_TIMEZONE,
) -> dict:
    """Idempotently seed Consultation event type + Mon-Fri 09:00-17:00 rules."""
    repo = store or vical_store
    existing = repo.get_event_type_by_slug(user_id, DEFAULT_SLUG)
    created_type = False
    if existing is None:
        existing = repo.create_event_type(
            user_id=user_id,
            slug=DEFAULT_SLUG,
            name=DEFAULT_NAME,
            host_user_id=user_id,
            duration_minutes=DEFAULT_DURATION_MINUTES,
            buffer_before_minutes=0,
            buffer_after_minutes=0,
            min_notice_minutes=0,
            horizon_days=30,
            location_mode="phone",
            requires_approval=False,
            requires_deposit=False,
            workspace_id=workspace_id,
            metadata={"seed": "echo_compat"},
        )
        created_type = True

    rules = repo.list_availability_rules(user_id, host_user_id=user_id, event_type_id=existing.id)
    # Also accept host-level rules with no event_type_id
    host_rules = repo.list_availability_rules(user_id, host_user_id=user_id)
    combined = rules or [r for r in host_rules if r.event_type_id is None]
    created_rules = 0
    if not combined:
        for day in range(0, 5):  # Monday-Friday
            repo.create_availability_rule(
                user_id=user_id,
                day_of_week=day,
                start_time=WEEKDAY_START,
                end_time=WEEKDAY_END,
                timezone=timezone,
                host_user_id=user_id,
                event_type_id=None,
                workspace_id=workspace_id,
            )
            created_rules += 1

    slug = user_id.strip().lower().replace(" ", "-") or "host"
    if repo.get_host_profile(user_id) is None:
        try:
            repo.upsert_host_profile(user_id, public_slug=slug, display_name=user_id)
        except ValueError:
            repo.upsert_host_profile(user_id, display_name=user_id)

    return {
        "event_type": existing,
        "created_event_type": created_type,
        "created_rules": created_rules,
        "host_profile": repo.get_host_profile(user_id),
    }
