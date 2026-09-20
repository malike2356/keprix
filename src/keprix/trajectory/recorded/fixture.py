"""Fixture schema, load/save, and scrubbing for recorded-session tests."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from keprix.trajectory.redaction import redact_payload
from keprix.trajectory.types import EVENT_TYPES

SCHEMA_VERSION = 1

_REQUIRED_TOP = frozenset({"schema_version", "fixture_id", "expectations", "events"})
_EVENT_REQUIRED = frozenset({"seq", "event_type", "payload"})


class FixtureValidationError(ValueError):
    """Raised when a recorded fixture fails schema or scrub checks."""


@dataclass
class RecordedFixture:
    """In-memory recorded trajectory fixture."""

    fixture_id: str
    expectations: dict[str, Any]
    events: list[dict[str, Any]]
    schema_version: int = SCHEMA_VERSION
    title: str = ""
    description: str = ""
    workspace_id: str = "fixture"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "fixture_id": self.fixture_id,
            "title": self.title,
            "description": self.description,
            "workspace_id": self.workspace_id,
            "expectations": self.expectations,
            "events": self.events,
        }


def scrub_fixture_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Deep-redact a fixture document before write or assert."""
    if not isinstance(data, dict):
        raise FixtureValidationError("fixture root must be an object")
    out = dict(data)
    out["expectations"] = redact_payload(out.get("expectations") or {})
    events_in = out.get("events") or []
    if not isinstance(events_in, list):
        raise FixtureValidationError("events must be a list")
    cleaned: list[dict[str, Any]] = []
    for raw in events_in:
        if not isinstance(raw, dict):
            raise FixtureValidationError("each event must be an object")
        item = dict(raw)
        item["payload"] = redact_payload(item.get("payload") or {})
        if item.get("error_text"):
            item["error_text"] = redact_payload(item["error_text"])
        cleaned.append(item)
    out["events"] = cleaned
    for key in ("title", "description", "fixture_id"):
        if key in out and isinstance(out[key], str):
            out[key] = redact_payload(out[key])
    return out


def validate_fixture_dict(data: dict[str, Any]) -> None:
    missing = _REQUIRED_TOP - set(data.keys())
    if missing:
        raise FixtureValidationError(f"missing keys: {sorted(missing)}")
    if int(data.get("schema_version") or 0) != SCHEMA_VERSION:
        raise FixtureValidationError(
            f"unsupported schema_version {data.get('schema_version')}; want {SCHEMA_VERSION}"
        )
    fixture_id = data.get("fixture_id")
    if not isinstance(fixture_id, str) or not fixture_id.strip():
        raise FixtureValidationError("fixture_id must be a non-empty string")
    expectations = data.get("expectations")
    if not isinstance(expectations, dict):
        raise FixtureValidationError("expectations must be an object")
    events = data.get("events")
    if not isinstance(events, list) or not events:
        raise FixtureValidationError("events must be a non-empty list")
    seen_seq: set[int] = set()
    for idx, event in enumerate(events):
        if not isinstance(event, dict):
            raise FixtureValidationError(f"events[{idx}] must be an object")
        miss = _EVENT_REQUIRED - set(event.keys())
        if miss:
            raise FixtureValidationError(f"events[{idx}] missing {sorted(miss)}")
        et = event["event_type"]
        if et not in EVENT_TYPES:
            raise FixtureValidationError(f"events[{idx}] unknown event_type: {et}")
        seq = int(event["seq"])
        if seq in seen_seq:
            raise FixtureValidationError(f"duplicate seq {seq}")
        seen_seq.add(seq)
        if not isinstance(event.get("payload"), dict):
            raise FixtureValidationError(f"events[{idx}].payload must be an object")
    # Fail closed on obvious unsanitized secrets still present as values.
    blob = json.dumps(data, ensure_ascii=False)
    for needle in ("sk-live-", "sk-proj-", "BEGIN PRIVATE KEY", "ghp_", "xoxb-"):
        if needle in blob:
            raise FixtureValidationError(
                f"fixture appears to contain unsanitized secret material ({needle})"
            )


def load_fixture(path: Path | str) -> RecordedFixture:
    path = Path(path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise FixtureValidationError("fixture JSON root must be an object")
    scrubbed = scrub_fixture_dict(raw)
    validate_fixture_dict(scrubbed)
    return RecordedFixture(
        fixture_id=str(scrubbed["fixture_id"]),
        expectations=dict(scrubbed["expectations"]),
        events=list(scrubbed["events"]),
        schema_version=int(scrubbed["schema_version"]),
        title=str(scrubbed.get("title") or ""),
        description=str(scrubbed.get("description") or ""),
        workspace_id=str(scrubbed.get("workspace_id") or "fixture"),
    )


def write_fixture(path: Path | str, data: dict[str, Any] | RecordedFixture) -> Path:
    """Write a scrubbed fixture. Owner-local only; never call from CI."""
    path = Path(path)
    payload = data.to_dict() if isinstance(data, RecordedFixture) else dict(data)
    scrubbed = scrub_fixture_dict(payload)
    validate_fixture_dict(scrubbed)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(scrubbed, indent=2, ensure_ascii=False, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    return path


def fixture_from_events(
    *,
    fixture_id: str,
    events: list[dict[str, Any]],
    expectations: dict[str, Any] | None = None,
    title: str = "",
    description: str = "",
    workspace_id: str = "fixture",
) -> RecordedFixture:
    """Build a fixture document from event dicts (export helper)."""
    normalized: list[dict[str, Any]] = []
    for idx, event in enumerate(sorted(events, key=lambda e: int(e.get("seq") or 0))):
        normalized.append(
            {
                "seq": int(event.get("seq") or idx + 1),
                "event_type": event["event_type"],
                "timestamp": event.get("timestamp") or "1970-01-01T00:00:00Z",
                "payload": dict(event.get("payload") or {}),
                "tool_name": event.get("tool_name"),
                "soft_wall_outcome": event.get("soft_wall_outcome"),
                "error_text": event.get("error_text"),
            }
        )
    data = scrub_fixture_dict(
        {
            "schema_version": SCHEMA_VERSION,
            "fixture_id": fixture_id,
            "title": title,
            "description": description,
            "workspace_id": workspace_id,
            "expectations": expectations
            or {
                "require_recorded_replay": True,
                "forbid_live_execute": True,
            },
            "events": normalized,
        }
    )
    validate_fixture_dict(data)
    return RecordedFixture(
        fixture_id=data["fixture_id"],
        expectations=data["expectations"],
        events=data["events"],
        schema_version=data["schema_version"],
        title=data.get("title") or "",
        description=data.get("description") or "",
        workspace_id=data.get("workspace_id") or "fixture",
    )
