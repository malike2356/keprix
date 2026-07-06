"""PostgreSQL dual-store tests for localization."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from keprix.backend.localization.store import LocalizationStore


@pytest.mark.asyncio
async def test_preferences_use_postgres_when_session_factory_available(tmp_path) -> None:
    store = LocalizationStore(base_dir=tmp_path)
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    mock_factory = MagicMock(return_value=mock_session)

    with patch("keprix.backend.localization.store.get_session_factory", return_value=mock_factory), patch(
        "keprix.backend.localization.store.ensure_localization_tables",
        new=AsyncMock(),
    ):
        saved = await store.upsert_preferences(
            "ws-pg",
            "user-pg",
            {"preferred_output_language": "ak-GH", "voice_output_enabled": True},
        )

    assert saved["workspace_id"] == "ws-pg"
    assert saved["user_id"] == "user-pg"
    assert saved["preferred_output_language"] == "ak-GH"
    mock_session.add.assert_called_once()
    mock_session.commit.assert_awaited()
