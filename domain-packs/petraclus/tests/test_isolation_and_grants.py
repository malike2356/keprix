"""Isolation and target-grant tests for Petraclus."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from conftest import PACK_ROOT, load_app
from fastapi.testclient import TestClient


def _invoke(client, capability: str, workspace_id: str, grants: list[str], input_data: dict):
    return client.post(
        "/v1/products/petraclus/invoke",
        json={
            "capability": capability,
            "workspace_id": workspace_id,
            "grants": grants,
            "input": {**input_data, "workspace_id": workspace_id, "purpose": input_data.get("purpose", "invoke")},
        },
    )


def test_cross_workspace_finding_denied() -> None:
    client = TestClient(load_app())
    response = _invoke(
        client,
        "finding_get",
        "ws-alpha",
        ["node:*"],
        {"finding_id": "finding-beta-1"},
    )
    assert response.status_code == 400
    assert "cross_workspace" in str(response.json()["detail"]).lower() or "not_found" in str(response.json()["detail"]).lower()


def test_expired_grant_blocks_scan_start() -> None:
    client = TestClient(load_app())
    client.post(
        "/v1/products/petraclus/approvals/appr-expired/decision",
        json={"approved": True, "actor_id": "tester", "input_hash": "hash-expired", "workspace_id": "ws-alpha"},
    )
    response = _invoke(
        client,
        "scan_start",
        "ws-alpha",
        ["node:*", "mutate"],
        {
            "target_grant_id": "grant-expired",
            "approval_id": "appr-expired",
            "input_hash": "hash-expired",
            "purpose": "active_scan",
        },
    )
    assert response.status_code == 400
    detail = str(response.json()["detail"])
    assert "expired" in detail.lower() or "target_grant" in detail.lower()


def test_revoked_grant_blocks_scan_start() -> None:
    client = TestClient(load_app())
    client.post(
        "/v1/products/petraclus/approvals/appr-revoked/decision",
        json={"approved": True, "actor_id": "tester", "input_hash": "hash-revoked", "workspace_id": "ws-alpha"},
    )
    response = _invoke(
        client,
        "scan_start",
        "ws-alpha",
        ["node:*", "mutate"],
        {
            "target_grant_id": "grant-revoked",
            "approval_id": "appr-revoked",
            "input_hash": "hash-revoked",
            "purpose": "active_scan",
        },
    )
    assert response.status_code == 400
    assert "revoked" in str(response.json()["detail"]).lower()


def test_read_only_cannot_mutate() -> None:
    client = TestClient(load_app())
    client.post(
        "/v1/products/petraclus/approvals/appr-ro/decision",
        json={"approved": True, "actor_id": "reader", "input_hash": "hash-ro", "workspace_id": "ws-alpha"},
    )
    response = _invoke(
        client,
        "scan_start",
        "ws-alpha",
        ["node:scan_start"],
        {
            "target_grant_id": "grant-valid",
            "approval_id": "appr-ro",
            "input_hash": "hash-ro",
            "purpose": "active_scan",
        },
    )
    assert response.status_code == 400
    assert "read_only" in str(response.json()["detail"]).lower() or "mutate" in str(response.json()["detail"]).lower()

    if str(PACK_ROOT) not in sys.path:
        sys.path.insert(0, str(PACK_ROOT))
    from tools import handlers

    raw = handlers.playbook_compose_handler(
        {
            "workspace_id": "ws-alpha",
            "grants": ["node:finding_get"],
            "purpose": "playbook",
            "nodes": ["finding_get", "scan_start"],
        }
    )
    data = json.loads(raw)
    assert data["status"] == "error"
