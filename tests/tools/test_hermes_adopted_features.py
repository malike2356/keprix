"""Tests for Hermes-adopted features: checkpoint manager, progressive tool disclosure,
x search tool validation (Prompt 280).
"""

from __future__ import annotations

import json
import tempfile
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ------------------------------------------------------------------ tool_search (progressive disclosure)

def test_bridge_tool_names_are_reserved():
    from keprix.tools.tool_search import BRIDGE_TOOL_NAMES, TOOL_CALL_NAME, TOOL_DESCRIBE_NAME, TOOL_SEARCH_NAME

    assert TOOL_SEARCH_NAME in BRIDGE_TOOL_NAMES
    assert TOOL_DESCRIBE_NAME in BRIDGE_TOOL_NAMES
    assert TOOL_CALL_NAME in BRIDGE_TOOL_NAMES
    assert len(BRIDGE_TOOL_NAMES) == 3


def test_token_estimation_char_count():
    from keprix.tools.tool_search import CHARS_PER_TOKEN

    # 4.0 chars per token is the documented rule-of-thumb
    assert CHARS_PER_TOKEN == 4.0


def test_bridge_tool_name_uniqueness():
    from keprix.tools.tool_search import BRIDGE_TOOL_NAMES

    # All three bridge tools must have distinct names
    assert len(BRIDGE_TOOL_NAMES) == 3


# ------------------------------------------------------------------ x_search_tool date validation

def test_x_search_valid_date_range_passes():
    from keprix.tools.x_search_tool import _validate_date_range

    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    # Should not raise
    _validate_date_range(yesterday, today)


def test_x_search_inverted_dates_raise():
    from keprix.tools.x_search_tool import _validate_date_range

    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    with pytest.raises((ValueError, Exception)):
        _validate_date_range(today, yesterday)


def test_x_search_malformed_date_raises():
    from keprix.tools.x_search_tool import _validate_date_range

    with pytest.raises((ValueError, Exception)):
        _validate_date_range("not-a-date", "also-bad")


def test_x_search_same_date_passes():
    from keprix.tools.x_search_tool import _validate_date_range

    today = date.today().isoformat()
    _validate_date_range(today, today)


# ------------------------------------------------------------------ checkpoint_manager

def test_checkpoint_manager_can_be_instantiated():
    from keprix.tools.checkpoint_manager import CheckpointManager

    cm = CheckpointManager()
    assert cm is not None


def test_checkpoint_manager_has_enabled_flag():
    from keprix.tools.checkpoint_manager import CheckpointManager

    cm = CheckpointManager(enabled=False)
    assert cm.enabled is False
    cm2 = CheckpointManager(enabled=True)
    assert cm2.enabled is True


def test_checkpoint_manager_max_snapshots_configurable():
    from keprix.tools.checkpoint_manager import CheckpointManager

    cm = CheckpointManager(max_snapshots=5)
    assert cm.max_snapshots == 5


def test_checkpoint_manager_list_when_disabled(tmp_path: Path):
    from keprix.tools.checkpoint_manager import CheckpointManager

    cm = CheckpointManager(enabled=False)
    result = cm.list_checkpoints(str(tmp_path))
    assert isinstance(result, list)


# ------------------------------------------------------------------ mixture_of_agents: model list

def test_moa_reference_models_are_defined():
    try:
        from keprix.tools.mixture_of_agents_tool import REFERENCE_MODELS
        assert isinstance(REFERENCE_MODELS, (list, tuple))
        assert len(REFERENCE_MODELS) >= 2
    except ImportError:
        pytest.skip("MoA tool has external deps not available in test env")


def test_moa_aggregator_model_is_defined():
    try:
        from keprix.tools.mixture_of_agents_tool import AGGREGATOR_MODEL
        assert isinstance(AGGREGATOR_MODEL, str)
        assert len(AGGREGATOR_MODEL) > 0
    except ImportError:
        pytest.skip("MoA tool has external deps not available in test env")
