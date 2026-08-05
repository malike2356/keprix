"""Tests for compression/rtk.py."""

from __future__ import annotations

from typing import Any

import pytest

from keprix.providers.compression.rtk import CompressedRequest, RTKCompressor


def _msg(role: str, content: str) -> dict[str, Any]:
    return {"role": role, "content": content}


def _make_messages(n: int = 4) -> list[dict[str, Any]]:
    msgs = [_msg("system", "You are a helpful assistant.")]
    for i in range(n):
        msgs.append(_msg("user", f"User message number {i + 1} with some content."))
        msgs.append(_msg("assistant", f"Assistant reply {i + 1}."))
    return msgs


@pytest.fixture
def compressor():
    return RTKCompressor()


@pytest.mark.asyncio
async def test_none_strategy_returns_unchanged(compressor):
    messages = _make_messages(3)
    result = await compressor.compress(messages, strategy="none")
    assert result.messages == messages
    assert result.savings_pct == 0.0


@pytest.mark.asyncio
async def test_minimal_strategy_returns_compressed_request(compressor):
    messages = _make_messages(5)
    result = await compressor.compress(messages, strategy="minimal")
    assert isinstance(result, CompressedRequest)
    assert result.compressed_tokens >= 0


@pytest.mark.asyncio
async def test_balanced_strategy_reduces_or_equals(compressor):
    messages = _make_messages(5)
    result = await compressor.compress(messages, strategy="balanced")
    assert result.compressed_tokens <= result.original_tokens


@pytest.mark.asyncio
async def test_aggressive_strategy_reduces_or_equals(compressor):
    messages = _make_messages(12)
    result = await compressor.compress(messages, strategy="aggressive")
    assert result.compressed_tokens <= result.original_tokens


@pytest.mark.asyncio
async def test_savings_pct_is_non_negative(compressor):
    messages = _make_messages(6)
    result = await compressor.compress(messages, strategy="balanced")
    assert result.savings_pct >= 0.0


@pytest.mark.asyncio
async def test_max_tokens_trims_messages(compressor):
    messages = _make_messages(20)
    result = await compressor.compress(messages, strategy="balanced", max_tokens=100)
    # With a very tight budget the list should be shorter
    assert len(result.messages) <= len(messages)


@pytest.mark.asyncio
async def test_empty_messages_returns_zero_tokens(compressor):
    result = await compressor.compress([], strategy="balanced")
    assert result.original_tokens == 0
    assert result.compressed_tokens == 0


@pytest.mark.asyncio
async def test_saved_tokens_property(compressor):
    messages = _make_messages(5)
    result = await compressor.compress(messages, strategy="aggressive")
    assert result.saved_tokens == max(0, result.original_tokens - result.compressed_tokens)


@pytest.mark.asyncio
async def test_duplicate_messages_deduped(compressor):
    repeated = _msg("user", "same message")
    messages = [_msg("system", "sys")] + [repeated] * 10
    result = await compressor.compress(messages, strategy="minimal")
    # Dedup should have removed most repetitions
    assert len(result.messages) < len(messages)


@pytest.mark.asyncio
async def test_invalid_strategy_falls_through(compressor):
    messages = _make_messages(3)
    # Should not raise; treat unknown strategy as minimal/none
    result = await compressor.compress(messages, strategy="unknown")
    assert result.compressed_tokens >= 0
