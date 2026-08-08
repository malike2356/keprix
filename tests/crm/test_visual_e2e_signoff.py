"""Contract-level visual CRM E2E sign-off checks (prompt 515)."""

from __future__ import annotations

from pathlib import Path


def test_ids_versions_states_compatible(tmp_path: Path, monkeypatch) -> None:
    from keprix.crm import metrics_semantic as ms
    from keprix.crm import pipeline_board as pb
    from keprix.crm import run_events as re
    from keprix.crm import workflow_graph as wg
    from keprix.crm.store import CrmStore
    from keprix.crm.visual_contract import RUNTIME_STATES, visual_contract_payload

    try:
        monkeypatch.setattr("keprix.auth.config.data_dir", lambda: str(tmp_path / "data"))
    except Exception:
        pass

    contract = visual_contract_payload()
    store = CrmStore(tmp_path / "e2e.db")
    ws = "ws_e2e"
    lead = store.create_lead(ws, name="Eve", email="eve@example.com", stage="discovered")

    board = pb.build_pipeline_board(ws, crm_store=store)
    assert board["workspace_id"] == ws

    graph = {
        "id": "wf_e2e",
        "name": "E2E",
        "status": "draft",
        "workflow_version": 1,
        "nodes": [
            {"id": "t", "family": "trigger", "type": "manual_trigger", "label": "T", "config": {}, "x": 0, "y": 0},
            {"id": "a", "family": "approval", "type": "soft_wall_approval", "label": "A", "config": {}, "x": 0, "y": 80},
            {"id": "s", "family": "outreach", "type": "email_send", "label": "S", "config": {}, "x": 0, "y": 160},
            {"id": "x", "family": "stop", "type": "stop", "label": "Stop", "config": {}, "x": 0, "y": 240},
        ],
        "edges": [
            {"id": "e1", "source": "t", "target": "a", "condition_label": "next"},
            {"id": "e2", "source": "a", "target": "s", "condition_label": "approved"},
            {"id": "e3", "source": "s", "target": "x", "condition_label": "next"},
        ],
    }
    assert wg.validate_graph(graph)["can_publish"] is True
    saved = wg.save_workflow_graph(ws, graph, actor_id="op")
    wid = saved["graph"]["id"]
    pub = wg.publish_workflow_graph(ws, wid, actor_id="op")
    assert pub["ok"] is True

    run = re.create_run(ws, workflow_id=wid, workflow_version=1, subject_id=lead["id"], graph=pub["graph"])
    snap = re.run_snapshot(ws, run["id"])
    assert snap["run"]["workflow_id"] == wid
    for st in snap["node_states"].values():
        assert st["state"] in RUNTIME_STATES or st["state"] in contract["runtime_states"]

    # Visual truth: no success before durable event
    assert all(st["state"] != "succeeded" for st in snap["node_states"].values())
    re.append_event(ws, run["id"], node_id="t", state="succeeded", detail={})
    snap2 = re.run_snapshot(ws, run["id"])
    assert snap2["node_states"]["t"]["state"] == "succeeded"

    ms.record_canonical_event(ws, "discovered", subject_ids={"lead_id": lead["id"]})
    q = ms.query_metrics(ws, crm_store=store)
    assert q["workspace_id"] == ws
    assert q["funnel"][0]["step"] == "discovered"


def test_frontend_visual_routes_exist() -> None:
    root = Path(__file__).resolve().parents[2] / "frontend" / "src" / "app" / "(workspace)" / "crm"
    for rel in (
        "pipeline/page.tsx",
        "workflows/[id]/page.tsx",
        "runs/[id]/page.tsx",
        "analytics/page.tsx",
        "ops/page.tsx",
    ):
        assert (root / rel).exists(), rel
