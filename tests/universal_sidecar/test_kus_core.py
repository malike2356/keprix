"""Tests for Keprix Universal Sidecar (KUS)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from keprix.universal_sidecar.conformance import minimal_manifest, reset_stores, run_conformance
from keprix.universal_sidecar.contract import architecture_summary, CONTRACT_VERSION
from keprix.universal_sidecar.manifest.validate import (
    diff_manifests,
    export_redacted,
    load_manifest,
    validate_manifest,
)
from keprix.universal_sidecar.nodes import validate_playbook_graph
from keprix.universal_sidecar.pairing import get_pairing_store
from keprix.universal_sidecar.registry import get_project_registry
from keprix.universal_sidecar.routes import router

EXAMPLES = Path(__file__).resolve().parents[2] / "src/keprix/universal_sidecar/manifest/examples"


@pytest.fixture(autouse=True)
def _reset():
    reset_stores()
    os.environ["KEPRIX_SIDECAR_DEV_OPEN"] = "1"
    yield
    reset_stores()


def test_architecture_summary():
    summary = architecture_summary()
    assert summary["contract"]["version"] == CONTRACT_VERSION
    assert "non_goals" in summary
    assert summary["openai_chat_compat"]


def test_minimal_manifest_validates():
    result = validate_manifest(EXAMPLES / "minimal.yaml")
    assert result.ok


def test_unknown_capability_fails():
    m = load_manifest(EXAMPLES / "minimal.yaml")
    m["capabilities"] = [{"node": "totally.unknown.node", "version": "1.0.0"}]
    result = validate_manifest(m)
    assert not result.ok


def test_manifest_cannot_embed_secret():
    m = load_manifest(EXAMPLES / "minimal.yaml")
    m["auth"]["api_key"] = "sk-live-supersecrettokenvalue"
    result = validate_manifest(m)
    assert not result.ok


def test_manifest_cannot_embed_hook():
    m = load_manifest(EXAMPLES / "minimal.yaml")
    m["hooks"] = {"pre_invoke": "os.system('id')"}
    result = validate_manifest(m)
    assert not result.ok


def test_diff_risky_requires_apply():
    old = load_manifest(EXAMPLES / "minimal.yaml")
    new = load_manifest(EXAMPLES / "read-plus-propose.yaml")
    diff = diff_manifests(old, new)
    assert "added_capabilities" in diff


def test_redacted_export_safe():
    m = load_manifest(EXAMPLES / "minimal.yaml")
    red = export_redacted(m)
    assert red["_redacted"] is True
    assert "DEMO_TOKEN" not in str(red.get("auth", {}))


def test_playbook_rejects_dangerous_node():
    graph = {
        "nodes": [{"id": "a", "node": "shell.exec"}],
        "edges": [],
    }
    result = validate_playbook_graph(graph)
    assert not result["ok"]


def test_pairing_replay_and_audience():
    get_project_registry().apply(minimal_manifest())
    store = get_pairing_store()
    created = store.create_code(
        project_key="demo",
        deployment="local",
        environment="local",
        base_url="http://127.0.0.1:9",
        callback_urls=[],
        requested_scopes=["discover", "invoke:summarise"],
    )
    approved = store.approve_code(created["code"])
    token = approved["access_token"]
    parsed = store.parse(token)
    assert parsed.project == "demo"
    with pytest.raises(ValueError):
        store.parse(token, expected_audience="wrong-aud")
    with pytest.raises(ValueError):
        store.approve_code(created["code"])


def test_delegated_actor_cannot_expand_grants():
    get_project_registry().apply(minimal_manifest())
    store = get_pairing_store()
    raw, workload = store.mint_token(
        project="demo",
        grants={"discover", "invoke:summarise"},
        purpose="test",
    )
    del raw
    delegated = store.delegate_actor(
        workload,
        actor_assertion={
            "actor_id": "user-1",
            "grants": ["discover", "administration", "invoke:summarise"],
            "signed_hash": "dev",
        },
    )
    assert "administration" not in delegated.grants
    assert "discover" in delegated.grants


def test_http_routes_health_and_capabilities():
    get_project_registry().apply(minimal_manifest())
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    assert client.get("/sidecar/v1/health").status_code == 200
    caps = client.get("/sidecar/v1/projects/demo/capabilities")
    assert caps.status_code == 200
    assert caps.json()["project_key"] == "demo"


def test_public_bind_refuses_without_secure_config(monkeypatch):
    from keprix.universal_sidecar import app as sidecar_app

    monkeypatch.setenv("KEPRIX_SIDECAR_HOST", "0.0.0.0")
    monkeypatch.delenv("KEPRIX_SIDECAR_ALLOW_PUBLIC", raising=False)
    monkeypatch.delenv("KEPRIX_UNIVERSAL_SIDECAR_TOKEN_SECRET", raising=False)
    monkeypatch.delenv("KEPRIX_PRODUCT_SIDECAR_TOKEN_SECRET", raising=False)
    monkeypatch.delenv("KEPRIX_SIDECAR_AUTH_SECRET", raising=False)
    monkeypatch.delenv("KEPRIX_SIDECAR_TLS_CERT", raising=False)
    with pytest.raises(SystemExit) as exc:
        sidecar_app._refuse_insecure_public_bind("0.0.0.0")
    assert exc.value.code == 2


def test_conformance_suite_passes():
    report = run_conformance(write_report=False)
    assert report["ok"] is True
    assert len(report["checks"]) >= 8


def test_memory_cross_project_isolation():
    from keprix.universal_sidecar.memory import get_memory_service

    get_project_registry().apply(minimal_manifest("demo"))
    get_project_registry().apply(minimal_manifest("other"))
    mem = get_memory_service()
    mem.write(project_key="demo", tenant_id="t1", namespace="ephemeral", content="secret-a", source="test")
    mem.write(project_key="other", tenant_id="t1", namespace="ephemeral", content="secret-b", source="test")
    hits = mem.search(project_key="demo", tenant_id="t1", query="secret")
    assert all(h["content"] != "secret-b" for h in hits)
    assert any("secret-a" in h["content"] for h in hits)
