"""Visual CRM contract and board/graph/metrics tests (prompts 506-515)."""

from __future__ import annotations

from pathlib import Path


def test_visual_contract_surfaces() -> None:
    from keprix.crm.visual_contract import visual_contract_payload

    payload = visual_contract_payload()
    assert "pipeline_board" in payload["surfaces"]
    assert "workflow_canvas" in payload["surfaces"]
    assert "execution_view" in payload["surfaces"]
    assert "analytics_dashboard" in payload["surfaces"]
    assert payload["routes"]["pipeline"] == "/crm/pipeline"
    assert "suppressed" in payload["runtime_states"]
    assert payload["state_legend"]["failed"]["label"] == "Failed"


def test_pipeline_board_and_transition(tmp_path: Path, monkeypatch) -> None:
    from keprix.crm.store import CrmStore
    from keprix.crm import pipeline_board as pb

    store = CrmStore(tmp_path / "crm.db")
    ws = "ws_visual"
    lead = store.create_lead(ws, name="Ada", email="ada@example.com", stage="discovered")
    board = pb.build_pipeline_board(ws, crm_store=store)
    assert board["lanes"]
    assert any(l["stage"] == "discovered" and l["count"] >= 1 for l in board["lanes"])

    denied = pb.preview_stage_transition(
        ws,
        crm_store=store,
        entity_type="lead",
        entity_id=lead["id"],
        to_stage="paying",
    )
    assert denied["allowed"] is False

    ok = pb.preview_stage_transition(
        ws,
        crm_store=store,
        entity_type="lead",
        entity_id=lead["id"],
        to_stage="enriched",
    )
    assert ok["allowed"] is True
    committed = pb.commit_stage_transition(
        ws,
        crm_store=store,
        entity_type="lead",
        entity_id=lead["id"],
        to_stage="enriched",
        actor_id="tester",
    )
    assert committed["ok"] is True
    assert store.get_lead(ws, lead["id"])["stage"] == "enriched"


def test_workflow_graph_validate_simulate_publish(tmp_path: Path, monkeypatch) -> None:
    from keprix.crm import workflow_graph as wg

    monkeypatch.setenv("HOME", str(tmp_path))
    # Point data_dir via auth if available; otherwise home fallback used
    try:
        monkeypatch.setattr("keprix.auth.config.data_dir", lambda: str(tmp_path / "data"))
    except Exception:
        pass

    graph = wg.template_graph("nurture")
    # template may lack soft wall; add approval for publish safety
    graph["nodes"].insert(
        1,
        {
            "id": "n_sw",
            "family": "approval",
            "type": "soft_wall_approval",
            "label": "Soft Wall",
            "config": {},
            "x": 40,
            "y": 120,
        },
    )
    graph["edges"].append({"id": "e_sw", "source": "n_0_list_trigger", "target": "n_sw", "condition_label": "next"})
    # ensure stop exists from template
    validation = wg.validate_graph(graph)
    assert "issues" in validation

    sim = wg.simulate_graph(graph)
    assert sim["external_side_effects"] is False

    saved = wg.save_workflow_graph("ws_g", graph, actor_id="a1")
    assert saved["ok"] is True
    wid = saved["graph"]["id"]
    # Fix graph to be publishable: ensure trigger+stop+approval
    g2 = wg.get_or_build_workflow_graph("ws_g", wid)
    # Force a minimal valid graph
    g2["nodes"] = [
        {"id": "t", "family": "trigger", "type": "manual_trigger", "label": "T", "config": {}, "x": 0, "y": 0},
        {"id": "a", "family": "approval", "type": "soft_wall_approval", "label": "A", "config": {}, "x": 0, "y": 80},
        {"id": "s", "family": "outreach", "type": "email_send", "label": "S", "config": {}, "x": 0, "y": 160},
        {"id": "x", "family": "stop", "type": "stop", "label": "Stop", "config": {}, "x": 0, "y": 240},
    ]
    g2["edges"] = [
        {"id": "e1", "source": "t", "target": "a", "condition_label": "next"},
        {"id": "e2", "source": "a", "target": "s", "condition_label": "approved"},
        {"id": "e3", "source": "s", "target": "x", "condition_label": "next"},
    ]
    wg.save_workflow_graph("ws_g", g2, actor_id="a1")
    published = wg.publish_workflow_graph("ws_g", wid, actor_id="a1")
    assert published["ok"] is True
    assert published["graph"]["status"] == "active"


def test_run_events_honest_animation(tmp_path: Path, monkeypatch) -> None:
    from keprix.crm import run_events as re
    from keprix.crm import workflow_graph as wg

    try:
        monkeypatch.setattr("keprix.auth.config.data_dir", lambda: str(tmp_path / "data"))
    except Exception:
        pass

    graph = {
        "id": "wf1",
        "workflow_version": 1,
        "nodes": [
            {"id": "n1", "family": "trigger", "type": "manual_trigger", "label": "Start", "x": 0, "y": 0},
            {"id": "n2", "family": "stop", "type": "stop", "label": "Stop", "x": 0, "y": 80},
        ],
        "edges": [{"id": "e1", "source": "n1", "target": "n2"}],
    }
    run = re.create_run("ws_r", workflow_id="wf1", graph=graph)
    snap1 = re.run_snapshot("ws_r", run["id"])
    assert snap1["animation_policy"]["only_on_durable_events"] is True
    assert snap1["node_states"]["n1"]["state"] == "upcoming"
    re.append_event("ws_r", run["id"], node_id="n1", state="active", detail={"message": "go"})
    page = re.run_events_since("ws_r", run["id"], cursor=0)
    assert page["events"]
    assert page["cursor"] >= 1
    # replay has no external effects by construction


def test_metrics_semantic_layer(tmp_path: Path, monkeypatch) -> None:
    from keprix.crm.store import CrmStore
    from keprix.crm import metrics_semantic as ms

    try:
        monkeypatch.setattr("keprix.auth.config.data_dir", lambda: str(tmp_path / "data"))
    except Exception:
        pass

    store = CrmStore(tmp_path / "m.db")
    ws = "ws_m"
    store.create_lead(ws, name="A", email="a@example.com", stage="enrolled")
    store.create_lead(ws, name="B", email="b@example.com", stage="engaged")
    back = ms.backfill_from_crm(ws, crm_store=store)
    assert back["ok"] is True
    q = ms.query_metrics(ws, crm_store=store, days=30)
    assert q["definition_version"] == ms.SEMANTIC_VERSION
    assert "unique_leads" in q["measures"]
    assert q["measures"]["unique_leads"]["definition"]["id"] == "unique_leads"
    assert q["funnel"]
    assert "hard_bounce_rate" in q["guards"]
    # Isolation: other workspace empty
    other = ms.query_metrics("other_ws", crm_store=store)
    assert other["measures"]["unique_leads"]["value"] in (0, 0.0, None) or other["incomplete_history"]


def test_node_inspector_redaction(tmp_path: Path, monkeypatch) -> None:
    from keprix.crm.node_inspector import build_inspector, create_support_bundle

    graph = {
        "id": "wf",
        "nodes": [
            {
                "id": "n1",
                "family": "outreach",
                "type": "email_send",
                "label": "Send",
                "config": {"api_key": "super-secret", "subject": "Hi"},
            },
            {"id": "n2", "family": "stop", "type": "stop", "label": "Stop", "config": {}},
            {"id": "n0", "family": "trigger", "type": "manual_trigger", "label": "T", "config": {}},
        ],
        "edges": [],
    }
    insp = build_inspector(mode="design", graph=graph, node_id="n1", workspace_id="ws")
    assert insp["ok"] is True
    assert insp["tabs"]["configuration"]["api_key"] == "[redacted]"
    bundle = create_support_bundle("ws", graph=graph, run=None, selected_node_ids=["n1"])
    assert bundle["redacted"] is True


def test_ops_centre_payload(tmp_path: Path) -> None:
    from keprix.crm.store import CrmStore
    from keprix.crm.ops_centre import build_ops_centre

    store = CrmStore(tmp_path / "o.db")
    ops = build_ops_centre("ws_ops", crm_store=store)
    assert "panels" in ops
    assert "active_runs" in ops["panels"]
    assert ops["transport"]["preferred"] == "polling"
    assert ops["telegram"]["signed_expiring_single_use"] is True
