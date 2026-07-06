"""Configuration optimizer: analyze telemetry and propose improvements."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from keprix.config.paths import overrides_env_file, proposals_file, rollback_file
from keprix.config.telemetry import JsonlTelemetryStore, TelemetryStore


@dataclass
class ConfigProposal:
    proposal_id: str
    category: str
    description: str
    current_value: Any
    proposed_value: Any
    rationale: str
    env_key: str
    risk: str  # "low" | "medium" | "high"
    created_at: float
    status: str = "pending"


def default_telemetry_store() -> TelemetryStore:
    from keprix.config.paths import get_data_dir

    return JsonlTelemetryStore(get_data_dir() / "telemetry.jsonl")


async def run_optimizer(telemetry_db: TelemetryStore | None = None) -> list[ConfigProposal]:
    store = telemetry_db or default_telemetry_store()
    proposals: list[ConfigProposal] = []

    provider_stats = await store.fetch_provider_stats(days=7)
    for provider, stats in provider_stats.items():
        if stats["error_rate"] > 0.15 and stats["call_count"] > 100:
            proposals.append(
                ConfigProposal(
                    proposal_id=f"llm-swap-{int(time.time())}-{provider}",
                    category="llm_routing",
                    description=(
                        f"Demote {provider} - {stats['error_rate'] * 100:.0f}% error rate over 7 days"
                    ),
                    current_value=provider,
                    proposed_value=stats["next_best_provider"],
                    rationale=f"{stats['call_count']} calls, {stats['error_count']} failures.",
                    env_key="KEPRIX_DEFAULT_LLM_PROVIDER",
                    risk="low",
                    created_at=time.time(),
                )
            )

    memory_stats = await store.fetch_memory_stats(days=7)
    if memory_stats["legitimate_drop_rate"] > 0.05:
        proposals.append(
            ConfigProposal(
                proposal_id=f"mem-ratelimit-{int(time.time())}",
                category="memory",
                description="Increase memory write rate limit - legitimate writes being dropped",
                current_value=memory_stats["current_limit"],
                proposed_value=min(memory_stats["current_limit"] * 2, 200),
                rationale=(
                    f"{memory_stats['legitimate_drop_rate'] * 100:.1f}% of non-injection writes dropped."
                ),
                env_key="KEPRIX_MEMORY_WRITE_LIMIT_PER_HOUR",
                risk="medium",
                created_at=time.time(),
            )
        )

    channel_stats = await store.fetch_channel_stats(days=7)
    for channel, stats in channel_stats.items():
        if stats["message_count"] == 0 and stats["enabled"]:
            proposals.append(
                ConfigProposal(
                    proposal_id=f"channel-disable-{channel}-{int(time.time())}",
                    category="channels",
                    description=f"Disable {channel} adapter - zero messages in 7 days",
                    current_value="enabled",
                    proposed_value="disabled",
                    rationale="Unused adapters are attack surface. Disable until needed.",
                    env_key=f"KEPRIX_{channel.upper()}_ENABLED",
                    risk="low",
                    created_at=time.time(),
                )
            )

    path = proposals_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        for proposal in proposals:
            handle.write(json.dumps(proposal.__dict__) + "\n")

    return proposals


async def apply_proposal(proposal_id: str, approved_by: str) -> bool:
    proposals = _load_pending_proposals()
    proposal = next((row for row in proposals if row["proposal_id"] == proposal_id), None)
    if not proposal:
        return False

    env_key = proposal["env_key"]
    proposed_value = proposal["proposed_value"]
    env_file = overrides_env_file()

    previous = _read_env_value(env_file, env_key)
    _append_rollback_record(env_key, previous, proposed_value, approved_by)

    _set_env_var(env_file, env_key, str(proposed_value))
    _mark_proposal_status(proposal_id, "applied")

    from keprix.security.event_reporter import report_security_event

    await report_security_event(
        "config_proposal_applied",
        "info",
        {
            "proposal_id": proposal_id,
            "approved_by": approved_by,
            "env_key": env_key,
            "new_value": str(proposed_value),
        },
    )
    return True


def reject_proposal(proposal_id: str) -> bool:
    proposals = _load_pending_proposals()
    if not any(row["proposal_id"] == proposal_id for row in proposals):
        return False
    _mark_proposal_status(proposal_id, "rejected")
    return True


async def rollback_env_var(env_key: str) -> bool:
    records = _load_rollback_records()
    match = next((row for row in reversed(records) if row["env_key"] == env_key), None)
    if not match:
        return False
    _set_env_var(overrides_env_file(), env_key, match["previous_value"])
    from keprix.security.event_reporter import report_security_event

    await report_security_event(
        "config_auto_repair",
        "info",
        {
            "action": "env_var_rollback",
            "env_key": env_key,
            "restored_value": match["previous_value"],
        },
    )
    return True


def _load_pending_proposals() -> list[dict[str, Any]]:
    path = proposals_file()
    if not path.exists():
        return []
    pending: list[dict[str, Any]] = []
    with path.open() as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("status", "pending") == "pending":
                pending.append(row)
    return pending


def _mark_proposal_status(proposal_id: str, status: str) -> None:
    path = proposals_file()
    if not path.exists():
        return
    rows: list[dict[str, Any]] = []
    with path.open() as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("proposal_id") == proposal_id:
                row["status"] = status
            rows.append(row)
    with path.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def _set_env_var(env_file: Path, key: str, value: str) -> None:
    lines = env_file.read_text().splitlines() if env_file.exists() else []
    updated = False
    result: list[str] = []
    for line in lines:
        if line.startswith(f"{key}="):
            result.append(f"{key}={value}")
            updated = True
        else:
            result.append(line)
    if not updated:
        result.append(f"{key}={value}")
    env_file.parent.mkdir(parents=True, exist_ok=True)
    env_file.write_text("\n".join(result) + "\n")


def _read_env_value(env_file: Path, key: str) -> str:
    if not env_file.exists():
        return ""
    for line in env_file.read_text().splitlines():
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1]
    return ""


def _append_rollback_record(
    env_key: str,
    previous_value: str,
    new_value: str,
    changed_by: str,
) -> None:
    path = rollback_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "env_key": env_key,
        "previous_value": previous_value,
        "new_value": new_value,
        "changed_by": changed_by,
        "changed_at": time.time(),
    }
    with path.open("a") as handle:
        handle.write(json.dumps(record) + "\n")


def _load_rollback_records() -> list[dict[str, Any]]:
    path = rollback_file()
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open() as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows
