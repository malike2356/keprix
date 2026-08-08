"""Template A/B experimentation with sticky cohorts and guardrails (prompt 455)."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from keprix.crm.nice_schema import ensure_nice_schema
from keprix.crm.soft_wall import gate_or_approve


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _loads(raw: Any, default: Any) -> Any:
    if isinstance(raw, (dict, list)):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw or json.dumps(default))
        except json.JSONDecodeError:
            return default
    return default


def _row(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    out = dict(row)
    out["variants"] = _loads(out.pop("variants_json", None) or out.get("variants"), [])
    out["traffic_split"] = _loads(out.pop("traffic_split_json", None) or out.get("traffic_split"), {})
    out["guard_thresholds"] = _loads(
        out.pop("guard_thresholds_json", None) or out.get("guard_thresholds"),
        {"complaint_rate": 0.01, "unsub_rate": 0.02},
    )
    out["metrics"] = _loads(out.pop("metrics_json", None) or out.get("metrics"), {})
    return out


def create_experiment(
    store: Any,
    workspace_id: str,
    *,
    name: str,
    variants: list[dict[str, Any]],
    traffic_split: dict[str, float] | None = None,
    sequence_id: str | None = None,
    min_sample: int = 50,
    guard_thresholds: dict[str, float] | None = None,
    actor_id: str | None = None,
) -> dict[str, Any]:
    ensure_nice_schema(store)
    ws = store._require_workspace(workspace_id)
    if len(variants) < 2:
        raise ValueError("at least two variants required")
    names = [str(v.get("id") or v.get("name") or f"v{i}") for i, v in enumerate(variants)]
    split = traffic_split or {n: round(1.0 / len(names), 4) for n in names}
    rid = str(uuid.uuid4())
    now = _utcnow()
    with store._lock:
        store._conn.execute(
            """
            INSERT INTO crm_experiments (
                id, workspace_id, name, sequence_id, status, variants_json, traffic_split_json,
                guard_thresholds_json, metrics_json, min_sample, actor_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, 'draft', ?, ?, ?, '{}', ?, ?, ?, ?)
            """,
            (
                rid,
                ws,
                name,
                sequence_id,
                json.dumps(variants, default=str),
                json.dumps(split),
                json.dumps(guard_thresholds or {"complaint_rate": 0.01, "unsub_rate": 0.02}),
                int(min_sample),
                actor_id,
                now,
                now,
            ),
        )
        store._conn.commit()
    return get_experiment(store, ws, rid)  # type: ignore[return-value]


def get_experiment(store: Any, workspace_id: str, experiment_id: str) -> dict[str, Any] | None:
    ensure_nice_schema(store)
    ws = store._require_workspace(workspace_id)
    return _row(
        store._fetchone(
            "SELECT * FROM crm_experiments WHERE workspace_id = ? AND id = ?",
            (ws, experiment_id),
        )
    )


def list_experiments(store: Any, workspace_id: str) -> list[dict[str, Any]]:
    ensure_nice_schema(store)
    ws = store._require_workspace(workspace_id)
    rows = store._fetchall(
        "SELECT * FROM crm_experiments WHERE workspace_id = ? ORDER BY created_at DESC",
        (ws,),
    )
    return [r for r in (_row(x) for x in rows) if r]


def assign_variant(store: Any, workspace_id: str, experiment_id: str, contact_key: str) -> str:
    """Sticky cohort assignment per contact_key."""
    ensure_nice_schema(store)
    ws = store._require_workspace(workspace_id)
    existing = store._fetchone(
        """
        SELECT * FROM crm_experiment_assignments
        WHERE workspace_id = ? AND experiment_id = ? AND contact_key = ?
        """,
        (ws, experiment_id, contact_key),
    )
    if existing:
        return str(existing["variant"])
    exp = get_experiment(store, ws, experiment_id)
    if not exp:
        raise ValueError("experiment_not_found")
    split = exp.get("traffic_split") or {}
    names = list(split.keys()) or [str(v.get("id") or v.get("name")) for v in exp.get("variants") or []]
    if not names:
        raise ValueError("no_variants")
    digest = hashlib.sha256(f"{experiment_id}:{contact_key}".encode()).hexdigest()
    bucket = int(digest[:8], 16) % 10000
    cumulative = 0.0
    chosen = names[-1]
    for name in names:
        cumulative += float(split.get(name, 1.0 / len(names))) * 10000
        if bucket < cumulative:
            chosen = name
            break
    rid = str(uuid.uuid4())
    with store._lock:
        store._conn.execute(
            """
            INSERT INTO crm_experiment_assignments (id, workspace_id, experiment_id, contact_key, variant, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (rid, ws, experiment_id, contact_key, chosen, _utcnow()),
        )
        store._conn.commit()
    return chosen


def record_metric(
    store: Any,
    workspace_id: str,
    experiment_id: str,
    *,
    variant: str,
    metric: str,
    amount: int = 1,
) -> dict[str, Any]:
    exp = get_experiment(store, workspace_id, experiment_id)
    if not exp:
        return {"ok": False, "error": "not_found"}
    metrics = dict(exp.get("metrics") or {})
    bucket = dict(metrics.get(variant) or {})
    bucket[metric] = int(bucket.get(metric) or 0) + amount
    metrics[variant] = bucket
    status = exp.get("status") or "draft"
    # Guardrails
    if status == "running":
        sends = max(1, int(bucket.get("send") or 0))
        complaint_rate = int(bucket.get("complaint") or 0) / sends
        unsub_rate = int(bucket.get("unsub") or 0) / sends
        thresholds = exp.get("guard_thresholds") or {}
        if complaint_rate > float(thresholds.get("complaint_rate", 0.01)) or unsub_rate > float(
            thresholds.get("unsub_rate", 0.02)
        ):
            status = "paused_guard"
    with store._lock:
        store._conn.execute(
            """
            UPDATE crm_experiments
            SET metrics_json = ?, status = ?, updated_at = ?
            WHERE workspace_id = ? AND id = ?
            """,
            (json.dumps(metrics), status, _utcnow(), workspace_id, experiment_id),
        )
        store._conn.commit()
    return {"ok": True, "experiment": get_experiment(store, workspace_id, experiment_id)}


def start_experiment(store: Any, workspace_id: str, experiment_id: str) -> dict[str, Any]:
    with store._lock:
        store._conn.execute(
            "UPDATE crm_experiments SET status = 'running', start_at = ?, updated_at = ? WHERE workspace_id = ? AND id = ?",
            (_utcnow(), _utcnow(), workspace_id, experiment_id),
        )
        store._conn.commit()
    return {"ok": True, "experiment": get_experiment(store, workspace_id, experiment_id)}


def results_table(store: Any, workspace_id: str, experiment_id: str) -> dict[str, Any]:
    exp = get_experiment(store, workspace_id, experiment_id)
    if not exp:
        return {"ok": False, "error": "not_found"}
    metrics = exp.get("metrics") or {}
    rows = []
    for variant, bucket in metrics.items():
        sends = int(bucket.get("send") or 0)
        rows.append(
            {
                "variant": variant,
                "send": sends,
                "reply": int(bucket.get("reply") or 0),
                "positive_reply": int(bucket.get("positive_reply") or 0),
                "unsub": int(bucket.get("unsub") or 0),
                "complaint": int(bucket.get("complaint") or 0),
                "book": int(bucket.get("book") or 0),
                "reply_rate": (int(bucket.get("reply") or 0) / sends) if sends else 0.0,
            }
        )
    min_sample = int(exp.get("min_sample") or 50)
    sample_ok = all(int((metrics.get(r["variant"]) or {}).get("send") or 0) >= min_sample for r in rows) if rows else False
    return {
        "ok": True,
        "experiment": exp,
        "rows": rows,
        "min_sample": min_sample,
        "sample_warning": not sample_ok,
        "sample_message": None
        if sample_ok
        else f"Minimum sample {min_sample} sends per variant not reached; do not declare a winner yet.",
    }


def promote_winner(
    store: Any,
    workspace_id: str,
    experiment_id: str,
    *,
    winner_variant: str,
    actor_id: str | None = None,
    force: bool = False,
    approval_id: str | None = None,
) -> dict[str, Any]:
    table = results_table(store, workspace_id, experiment_id)
    if not table.get("ok"):
        return table
    if table.get("sample_warning") and not force:
        return {
            "ok": False,
            "error": "min_sample_not_met",
            "message": table.get("sample_message"),
            "results": table,
        }
    gate = gate_or_approve(
        workspace_id,
        kind="experiment_promote_winner",
        subject=f"Promote experiment winner {winner_variant}",
        payload={"experiment_id": experiment_id, "winner": winner_variant},
        object_type="experiment",
        object_id=experiment_id,
        actor_id=actor_id,
        force=force,
        approval_id=approval_id,
    )
    if gate.get("blocked"):
        return {"ok": False, "blocked": True, "approval": gate.get("approval")}
    with store._lock:
        store._conn.execute(
            """
            UPDATE crm_experiments
            SET winner_variant = ?, status = 'winner_promoted', updated_at = ?
            WHERE workspace_id = ? AND id = ?
            """,
            (winner_variant, _utcnow(), workspace_id, experiment_id),
        )
        store._conn.commit()
    exp = get_experiment(store, workspace_id, experiment_id)
    winner = next((v for v in (exp or {}).get("variants") or [] if str(v.get("id") or v.get("name")) == winner_variant), None)
    return {
        "ok": True,
        "experiment": exp,
        "promoted_template": winner,
        "note": "Sequence template update is Soft Wall gated; apply winner subject/body under Soft Wall.",
    }
