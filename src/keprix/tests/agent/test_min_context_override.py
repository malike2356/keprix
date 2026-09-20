"""Tests for the configurable minimum-context floor (small local models)."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from agent.model_metadata import (
    ABSOLUTE_MINIMUM_CONTEXT_LENGTH,
    MIN_CONTEXT_ENV_VAR,
    MINIMUM_CONTEXT_LENGTH,
    compute_compression_threshold,
    get_context_warning_threshold,
    get_minimum_context_length,
    is_context_floor_enforced,
)


@pytest.fixture(autouse=True)
def _no_env_no_config(monkeypatch):
    """Start every test with no env var and an empty config."""
    monkeypatch.delenv(MIN_CONTEXT_ENV_VAR, raising=False)
    with patch("keprix_cli.config.load_config_readonly", return_value={}):
        yield


def _config(value):
    return patch(
        "keprix_cli.config.load_config_readonly",
        return_value={"agent": {"min_context_length": value}},
    )


class TestGetMinimumContextLength:
    def test_default_is_64k(self):
        assert get_minimum_context_length() == MINIMUM_CONTEXT_LENGTH == 64_000
        assert is_context_floor_enforced()

    def test_env_lowers_floor(self, monkeypatch):
        monkeypatch.setenv(MIN_CONTEXT_ENV_VAR, "16000")
        assert get_minimum_context_length() == 16_000

    def test_env_accepts_separators(self, monkeypatch):
        monkeypatch.setenv(MIN_CONTEXT_ENV_VAR, "32,768")
        assert get_minimum_context_length() == 32_768

    def test_config_lowers_floor(self):
        with _config(24_000):
            assert get_minimum_context_length() == 24_000

    def test_env_beats_config(self, monkeypatch):
        monkeypatch.setenv(MIN_CONTEXT_ENV_VAR, "16000")
        with _config(24_000):
            assert get_minimum_context_length() == 16_000

    def test_can_raise_floor(self, monkeypatch):
        monkeypatch.setenv(MIN_CONTEXT_ENV_VAR, "128000")
        assert get_minimum_context_length() == 128_000

    def test_clamped_to_absolute_minimum(self, monkeypatch):
        monkeypatch.setenv(MIN_CONTEXT_ENV_VAR, "1000")
        assert get_minimum_context_length() == ABSOLUTE_MINIMUM_CONTEXT_LENGTH

    def test_zero_disables_enforcement(self, monkeypatch):
        monkeypatch.setenv(MIN_CONTEXT_ENV_VAR, "0")
        assert get_minimum_context_length() == 0
        assert not is_context_floor_enforced()

    @pytest.mark.parametrize("bad", ["abc", "-5", "1.5e4", "  "])
    def test_invalid_env_falls_back_to_default(self, monkeypatch, bad):
        monkeypatch.setenv(MIN_CONTEXT_ENV_VAR, bad)
        assert get_minimum_context_length() == MINIMUM_CONTEXT_LENGTH

    @pytest.mark.parametrize("bad", ["abc", -1, True, None, [16000]])
    def test_invalid_config_falls_back_to_default(self, bad):
        with _config(bad):
            assert get_minimum_context_length() == MINIMUM_CONTEXT_LENGTH

    def test_non_dict_agent_section_is_ignored(self):
        with patch("keprix_cli.config.load_config_readonly", return_value={"agent": "x"}):
            assert get_minimum_context_length() == MINIMUM_CONTEXT_LENGTH

    def test_config_load_failure_falls_back_to_default(self):
        with patch("keprix_cli.config.load_config_readonly", side_effect=RuntimeError("boom")):
            assert get_minimum_context_length() == MINIMUM_CONTEXT_LENGTH


class TestWarningThreshold:
    def test_matches_floor_normally(self, monkeypatch):
        monkeypatch.setenv(MIN_CONTEXT_ENV_VAR, "16000")
        assert get_context_warning_threshold() == 16_000

    def test_warn_only_mode_still_recommends_default(self, monkeypatch):
        monkeypatch.setenv(MIN_CONTEXT_ENV_VAR, "0")
        assert get_context_warning_threshold() == MINIMUM_CONTEXT_LENGTH


class TestCompressionThreshold:
    def test_unchanged_for_large_context(self):
        assert compute_compression_threshold(200_000, 0.50) == 100_000

    def test_floor_still_applies_at_minimum_window(self):
        # 64K window, 50% -> 32K, floor lifts it to 64K (existing behaviour).
        assert compute_compression_threshold(64_000, 0.50) == 64_000

    def test_default_floor_never_exceeds_small_window(self):
        # Old formula gave 64K for a 32K window -> compression never fired.
        assert compute_compression_threshold(32_768, 0.50) == 16_384

    def test_lowered_floor_on_small_window(self, monkeypatch):
        monkeypatch.setenv(MIN_CONTEXT_ENV_VAR, "16000")
        assert compute_compression_threshold(32_768, 0.50) == 16_384
        assert compute_compression_threshold(32_768, 0.30) == 16_000

    def test_warn_only_mode_uses_plain_percentage(self, monkeypatch):
        monkeypatch.setenv(MIN_CONTEXT_ENV_VAR, "0")
        assert compute_compression_threshold(32_768, 0.50) == 16_384


class TestOllamaRuntimeGuard:
    def _agent(self, ctx):
        return SimpleNamespace(
            tools=[{"type": "function"}],
            _ollama_num_ctx=ctx,
            model="qwen3:4b",
            base_url="http://localhost:11434/v1",
            provider="custom",
            session_id="s1",
        )

    def test_blocks_below_default_floor(self):
        from agent.conversation_loop import _ollama_context_limit_error

        msg = _ollama_context_limit_error(self._agent(32_768), 5_000)
        assert msg and "64,000" in msg

    def test_lowered_floor_allows_small_context(self, monkeypatch):
        from agent.conversation_loop import _ollama_context_limit_error

        monkeypatch.setenv(MIN_CONTEXT_ENV_VAR, "16000")
        assert _ollama_context_limit_error(self._agent(32_768), 5_000) is None

    def test_lowered_floor_still_blocks_tinier_context(self, monkeypatch):
        from agent.conversation_loop import _ollama_context_limit_error

        monkeypatch.setenv(MIN_CONTEXT_ENV_VAR, "16000")
        msg = _ollama_context_limit_error(self._agent(8_192), 5_000)
        assert msg and "16,000" in msg

    def test_warn_only_mode_never_blocks(self, monkeypatch):
        from agent.conversation_loop import _ollama_context_limit_error

        monkeypatch.setenv(MIN_CONTEXT_ENV_VAR, "0")
        assert _ollama_context_limit_error(self._agent(4_096), 5_000) is None
