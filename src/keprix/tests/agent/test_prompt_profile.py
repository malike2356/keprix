"""Tests for the ``compact`` prompt profile (small local models)."""

from unittest.mock import patch

import pytest

from agent.prompt_builder import (
    build_skills_system_prompt,
    clear_skills_system_prompt_cache,
)
from agent.prompt_profile import (
    COMPACT_CORE_TOOLS,
    PROFILE_ENV_VAR,
    compact_tool_allowlist,
    filter_tools_for_profile,
    get_prompt_profile,
    is_compact_profile,
)


def _tool(name):
    return {"type": "function", "function": {"name": name, "description": "d", "parameters": {}}}


def _names(tools):
    return [t["function"]["name"] for t in tools]


def _config(agent_cfg):
    return patch("keprix_cli.config.load_config_readonly", return_value={"agent": agent_cfg})


@pytest.fixture(autouse=True)
def _no_env_no_config(monkeypatch):
    monkeypatch.delenv(PROFILE_ENV_VAR, raising=False)
    with patch("keprix_cli.config.load_config_readonly", return_value={}):
        yield


class TestProfileSelection:
    def test_default_is_full(self):
        assert get_prompt_profile() == "full"
        assert not is_compact_profile()

    def test_env_selects_compact(self, monkeypatch):
        monkeypatch.setenv(PROFILE_ENV_VAR, "compact")
        assert is_compact_profile()

    def test_env_is_case_and_space_insensitive(self, monkeypatch):
        monkeypatch.setenv(PROFILE_ENV_VAR, "  Compact ")
        assert is_compact_profile()

    def test_config_selects_compact(self):
        with _config({"prompt_profile": "compact"}):
            assert is_compact_profile()

    def test_env_beats_config(self, monkeypatch):
        monkeypatch.setenv(PROFILE_ENV_VAR, "full")
        with _config({"prompt_profile": "compact"}):
            assert get_prompt_profile() == "full"

    @pytest.mark.parametrize("bad", ["tiny", "COMPACTT", "1", 5])
    def test_unknown_value_falls_back_to_full(self, bad):
        with _config({"prompt_profile": bad}):
            assert get_prompt_profile() == "full"

    def test_non_dict_agent_section_falls_back_to_full(self):
        with patch("keprix_cli.config.load_config_readonly", return_value={"agent": "x"}):
            assert get_prompt_profile() == "full"


class TestToolFilter:
    TOOLS = [
        _tool(n)
        for n in (
            "terminal", "read_file", "patch", "web_search", "todo",
            "delegate_task", "session_search", "skill_manage", "browser_click",
            "kanban_create", "channel_config", "mcp_github_create_issue",
            "tool_search", "tool_describe", "tool_call", "create_lead",
        )
    ]

    def test_full_profile_is_a_noop(self):
        assert filter_tools_for_profile(self.TOOLS) is self.TOOLS

    def test_compact_keeps_core_mcp_and_bridge_tools(self, monkeypatch):
        monkeypatch.setenv(PROFILE_ENV_VAR, "compact")
        kept = _names(filter_tools_for_profile(self.TOOLS))
        assert kept == [
            "terminal", "read_file", "patch", "web_search", "todo",
            "mcp_github_create_issue", "tool_search", "tool_describe", "tool_call",
        ]

    def test_compact_drops_heavy_and_admin_tools(self, monkeypatch):
        monkeypatch.setenv(PROFILE_ENV_VAR, "compact")
        kept = set(_names(filter_tools_for_profile(self.TOOLS)))
        for dropped in ("delegate_task", "session_search", "skill_manage",
                        "browser_click", "kanban_create", "channel_config", "create_lead"):
            assert dropped not in kept

    def test_compact_tools_config_extends_allowlist(self, monkeypatch):
        monkeypatch.setenv(PROFILE_ENV_VAR, "compact")
        with _config({"compact_tools": ["browser_click", " create_lead "]}):
            kept = set(_names(filter_tools_for_profile(self.TOOLS)))
            assert {"browser_click", "create_lead"} <= kept
            assert "delegate_task" not in kept

    def test_compact_tools_accepts_single_string(self):
        with _config({"compact_tools": "delegate_task"}):
            assert "delegate_task" in compact_tool_allowlist()

    def test_compact_tools_garbage_is_ignored(self):
        with _config({"compact_tools": 42}):
            assert compact_tool_allowlist() == COMPACT_CORE_TOOLS

    def test_core_allowlist_names_exist_in_keprix_cli_toolset(self):
        """Guard against typos / renamed tools in the allow-list."""
        import toolsets

        resolved = set(toolsets.resolve_toolset("keprix-cli"))
        assert COMPACT_CORE_TOOLS <= resolved, COMPACT_CORE_TOOLS - resolved


class TestSkillsIndexNamesOnly:
    @pytest.fixture(autouse=True)
    def _clear_cache(self):
        clear_skills_system_prompt_cache(clear_snapshot=True)
        yield
        clear_skills_system_prompt_cache(clear_snapshot=True)

    @pytest.fixture
    def skills(self, monkeypatch, tmp_path):
        monkeypatch.setenv("KEPRIX_HOME", str(tmp_path))
        for cat, name in (("coding", "python-debug"), ("github", "pr-review")):
            d = tmp_path / "skills" / cat / name
            d.mkdir(parents=True)
            (d / "SKILL.md").write_text(
                f"---\nname: {name}\ndescription: A long description of {name}\n---\n"
            )

    def test_names_only_lists_every_name_without_descriptions(self, skills):
        result = build_skills_system_prompt(names_only=True)
        assert "python-debug" in result and "pr-review" in result
        assert "A long description" not in result
        assert "[names only]" not in result
        assert "<available_skills>" in result

    def test_names_only_uses_short_preamble(self, skills):
        full = build_skills_system_prompt()
        compact = build_skills_system_prompt(names_only=True)
        assert "mandatory" in full and "mandatory" not in compact
        assert len(compact) < len(full) / 2
        assert "skill_view(name)" in compact

    def test_full_output_unchanged_by_default(self, skills):
        result = build_skills_system_prompt()
        assert "A long description of python-debug" in result
        assert "## Skills (mandatory)" in result

    def test_names_only_and_full_do_not_share_a_cache_entry(self, skills):
        first = build_skills_system_prompt(names_only=True)
        second = build_skills_system_prompt()
        third = build_skills_system_prompt(names_only=True)
        assert first != second
        assert first == third

    def test_names_only_with_no_skills_is_empty(self, monkeypatch, tmp_path):
        monkeypatch.setenv("KEPRIX_HOME", str(tmp_path))
        assert build_skills_system_prompt(names_only=True) == ""


class TestLocalContextCap:
    def test_no_cap_in_full_profile(self):
        from agent.prompt_profile import cap_local_context, compact_context_cap

        assert compact_context_cap() is None
        assert cap_local_context(262_144) == 262_144

    def test_default_cap_in_compact_profile(self, monkeypatch):
        from agent.prompt_profile import DEFAULT_COMPACT_CONTEXT_CAP, cap_local_context

        monkeypatch.setenv(PROFILE_ENV_VAR, "compact")
        assert cap_local_context(262_144) == DEFAULT_COMPACT_CONTEXT_CAP == 32_768

    def test_smaller_window_is_left_alone(self, monkeypatch):
        from agent.prompt_profile import cap_local_context

        monkeypatch.setenv(PROFILE_ENV_VAR, "compact")
        assert cap_local_context(16_384) == 16_384

    def test_config_overrides_cap(self, monkeypatch):
        from agent.prompt_profile import cap_local_context

        monkeypatch.setenv(PROFILE_ENV_VAR, "compact")
        with _config({"compact_context_cap": 24_000}):
            assert cap_local_context(262_144) == 24_000

    def test_zero_disables_cap(self, monkeypatch):
        from agent.prompt_profile import cap_local_context, compact_context_cap

        monkeypatch.setenv(PROFILE_ENV_VAR, "compact")
        with _config({"compact_context_cap": 0}):
            assert compact_context_cap() is None
            assert cap_local_context(262_144) == 262_144

    @pytest.mark.parametrize("bad", ["big", None, True, [1]])
    def test_bad_value_uses_default(self, monkeypatch, bad):
        from agent.prompt_profile import DEFAULT_COMPACT_CONTEXT_CAP, compact_context_cap

        monkeypatch.setenv(PROFILE_ENV_VAR, "compact")
        with _config({"compact_context_cap": bad}):
            assert compact_context_cap() == DEFAULT_COMPACT_CONTEXT_CAP

    def test_cap_never_below_minimum_floor(self, monkeypatch):
        from agent.prompt_profile import compact_context_cap

        monkeypatch.setenv(PROFILE_ENV_VAR, "compact")
        monkeypatch.setenv("KEPRIX_MIN_CONTEXT_LENGTH", "20000")
        with _config({"compact_context_cap": 10_000}):
            assert compact_context_cap() == 20_000
