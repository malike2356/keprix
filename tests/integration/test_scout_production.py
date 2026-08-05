"""Tests for production Scout helpers and product registry."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from keprix.integrations.product_registry import list_registered_products, register_product
from keprix.integrations.scout_production import (
    products_health_payload,
    scout_test_command,
    security_layers_payload,
)


@pytest.mark.asyncio
async def test_scout_test_command_executes_locally():
    result = await scout_test_command()
    assert "ok" in result
    assert result.get("result", {}).get("status") == "executed"


def test_product_register_and_list(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    register_product(
        "abbis",
        scout_enabled=True,
        personas=["SDR"],
        tools=["web_search"],
        security_policy="standard",
    )
    products = list_registered_products()
    assert len(products) == 1
    assert products[0]["product_id"] == "abbis"


def test_security_layers_payload_contains_core_layers():
    payload = security_layers_payload()
    assert payload["prompt_guard"]["present"] is True
    assert "mode" in payload["prompt_guard"]
    assert payload["egress_gate"]["present"] is True
    assert payload["tool_acl"]["present"] is True


def test_products_health_payload():
    payload = products_health_payload()
    assert "count" in payload
    assert "products" in payload
