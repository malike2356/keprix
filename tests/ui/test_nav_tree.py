"""Tests for ui_contract nav_tree and discovery modules (Prompt 276)."""

from __future__ import annotations

import pytest

from keprix.ui_contract.discovery import (
    DISCOVERY_CARDS,
    DISCOVERY_CARDS_BY_PRIORITY,
    DiscoveryCard,
    select_card,
)
from keprix.ui_contract.empty_states import EMPTY_STATES
from keprix.ui_contract.nav_tree import (
    NAV_TREE,
    all_paths,
    get_route,
    top_level_for_role,
    top_level_for_surface,
    to_dict,
)


# ------------------------------------------------------------------ nav tree

def test_home_route_is_root():
    home = get_route("home")
    assert home is not None
    assert home.path == "/"


def test_admin_is_operator_only():
    admin = get_route("admin")
    assert admin is not None
    assert admin.operator_only is True


def test_admin_hidden_from_product_surfaces():
    admin = get_route("admin")
    for surface in ("aiva", "abbis", "petraclus"):
        visible = top_level_for_surface(surface)
        assert admin not in visible


def test_admin_visible_on_keprix_native_surface():
    visible = top_level_for_surface("keprix")
    admin = get_route("admin")
    assert admin in visible


def test_admin_visible_to_admin_role():
    items = top_level_for_role("admin")
    ids = {r.id for r in items}
    assert "admin" in ids


def test_admin_hidden_from_user_role():
    items = top_level_for_role("user")
    ids = {r.id for r in items}
    assert "admin" not in ids


def test_top_level_has_all_main_sections():
    ids = {r.id for r in NAV_TREE}
    for expected in ("home", "chat", "brain", "skills", "tasks", "tools", "voice", "settings", "admin"):
        assert expected in ids, f"Missing top-level section: {expected}"


def test_brain_has_graph_and_health_children():
    brain = get_route("brain")
    child_ids = {c.id for c in brain.children}
    assert "brain_graph" in child_ids
    assert "brain_health" in child_ids
    assert "brain_replay" in child_ids


def test_all_paths_are_non_empty_strings():
    paths = all_paths()
    assert len(paths) > 0
    for p in paths:
        assert isinstance(p, str)
        assert p.startswith("/")


def test_settings_has_billing_child():
    settings = get_route("settings")
    child_ids = {c.id for c in settings.children}
    assert "settings_billing" in child_ids


def test_admin_has_isolation_audit_child():
    admin = get_route("admin")
    child_ids = {c.id for c in admin.children}
    assert "admin_isolation_audit" in child_ids


def test_to_dict_structure():
    d = to_dict(get_route("home"))
    assert d["id"] == "home"
    assert d["path"] == "/"
    assert "children" in d
    assert "operator_only" in d


def test_unknown_route_returns_none():
    assert get_route("nonexistent_route") is None


# ------------------------------------------------------------------ discovery

def test_discovery_cards_are_sorted_by_priority():
    priorities = [c.priority for c in DISCOVERY_CARDS_BY_PRIORITY]
    assert priorities == sorted(priorities)


def test_quota_warning_highest_priority():
    assert DISCOVERY_CARDS_BY_PRIORITY[0].id == "quota_warning"


def test_select_quota_card_when_over_80():
    ctx = {"quota_pct": 85}
    card = select_card(ctx)
    assert card is not None
    assert card.id == "quota_warning"


def test_quota_card_not_selected_when_under_threshold():
    ctx = {"quota_pct": 75}
    card = select_card(ctx)
    assert card is None or card.id != "quota_warning"


def test_brain_health_card_when_score_below_60():
    ctx = {"brain_health_score": 45}
    card = select_card(ctx)
    assert card is not None
    assert card.id == "brain_health_low"


def test_discover_brain_when_memories_sufficient_and_not_visited():
    ctx = {"memories": 15, "brain_never_opened": True}
    card = select_card(ctx)
    assert card is not None
    assert card.id == "discover_brain"


def test_discover_brain_not_shown_when_already_visited():
    ctx = {"memories": 15, "brain_never_opened": False}
    card = select_card(ctx)
    assert card is None or card.id != "discover_brain"


def test_discover_skills_when_sessions_high_and_no_skills():
    ctx = {"sessions": 6, "skills_count": 0}
    card = select_card(ctx)
    assert card is not None
    assert card.id == "discover_skills"


def test_discover_voice_when_old_workspace_no_phone():
    ctx = {"voice_not_provisioned": True, "workspace_age_days": 45}
    card = select_card(ctx)
    assert card is not None
    assert card.id == "discover_voice"


def test_discover_playbooks_when_tasks_done_no_playbooks():
    ctx = {"tasks_completed": 3, "playbooks_count": 0}
    card = select_card(ctx)
    assert card is not None
    assert card.id == "discover_playbooks"


def test_dismissed_card_skipped():
    ctx = {"quota_pct": 90, "brain_health_score": 40}
    dismissed = {"quota_warning"}
    card = select_card(ctx, dismissed_ids=dismissed)
    assert card is not None
    assert card.id == "brain_health_low"


def test_acted_on_card_skipped():
    ctx = {"quota_pct": 90}
    acted = {"quota_warning"}
    card = select_card(ctx, acted_on_ids=acted)
    assert card is None or card.id != "quota_warning"


def test_no_card_when_all_conditions_false():
    ctx = {}
    card = select_card(ctx)
    assert card is None


def test_quota_card_target_is_billing():
    card = next(c for c in DISCOVERY_CARDS if c.id == "quota_warning")
    assert "/settings/billing" in card.target_path or "/admin/quotas" in card.target_path


def test_all_cards_have_required_fields():
    for card in DISCOVERY_CARDS:
        assert card.id
        assert card.text
        assert card.action_label
        assert card.target_path.startswith("/")
        assert card.priority >= 1


# ------------------------------------------------------------------ empty states

def test_empty_states_cover_all_main_sections():
    required = {"home", "chat", "brain_graph", "skills", "tasks", "tools", "voice"}
    for key in required:
        assert key in EMPTY_STATES, f"Missing empty state for: {key}"


def test_empty_states_have_required_fields():
    for key, state in EMPTY_STATES.items():
        assert "title" in state, f"Missing title in empty state: {key}"
        assert "description" in state, f"Missing description in empty state: {key}"
        assert "No data" not in state["title"], f"Generic empty state title in: {key}"


def test_empty_state_titles_use_plain_language():
    for key, state in EMPTY_STATES.items():
        title = state["title"].lower()
        assert "null" not in title
        assert "entity" not in title
        assert "n/a" not in title


def test_no_em_dashes_in_empty_states():
    import json
    blob = json.dumps(EMPTY_STATES)
    assert "—" not in blob
    assert "–" not in blob
