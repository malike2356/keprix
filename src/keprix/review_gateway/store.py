"""File-backed review request store."""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _data_root() -> Path:
    env = os.environ.get("KEPRIX_DATA_DIR", "").strip()
    if env:
        return Path(env)
    try:
        from keprix_cli.config import get_keprix_home

        return Path(get_keprix_home())
    except Exception:
        return Path.home() / ".keprix"


def _store_dir() -> Path:
    root = _data_root() / "review_gateway"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ReviewDecision:
    id: str
    review_request_id: str
    action: str
    reviewer_note: str
    token_id: str
    reviewer_ip_hash: str
    decided_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReviewRequest:
    id: str
    workspace_id: str
    title: str
    context_message: str
    artifact_type: str
    artifact_content: str
    artifact_url: str
    artifact_filename: str
    reviewer_name: str
    reviewer_email: str
    reviewer_webhook_url: str
    allowed_actions: list[str]
    token_id: str
    expires_at: str
    reminder_at: str | None
    status: str
    playbook_run_id: str | None
    playbook_step_id: str | None
    created_at: str
    created_by_user_id: str | None
    domain_pack: str = ""
    decision: ReviewDecision | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if self.decision:
            payload["decision"] = self.decision.to_dict()
        return payload

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> ReviewRequest:
        decision = row.get("decision")
        return cls(
            id=row["id"],
            workspace_id=row["workspace_id"],
            title=row["title"],
            context_message=row.get("context_message", ""),
            artifact_type=row["artifact_type"],
            artifact_content=row.get("artifact_content", ""),
            artifact_url=row.get("artifact_url", ""),
            artifact_filename=row.get("artifact_filename", ""),
            reviewer_name=row["reviewer_name"],
            reviewer_email=row["reviewer_email"],
            reviewer_webhook_url=row.get("reviewer_webhook_url", ""),
            allowed_actions=list(row.get("allowed_actions") or ["approve", "reject"]),
            token_id=row["token_id"],
            expires_at=row["expires_at"],
            reminder_at=row.get("reminder_at"),
            status=row.get("status", "pending"),
            playbook_run_id=row.get("playbook_run_id"),
            playbook_step_id=row.get("playbook_step_id"),
            domain_pack=str(row.get("domain_pack") or ""),
            created_at=row.get("created_at", _utcnow().isoformat()),
            created_by_user_id=row.get("created_by_user_id"),
            decision=ReviewDecision(**decision) if decision else None,
        )


class ReviewStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self._dir = base_dir or _store_dir()
        self._path = self._dir / "requests.json"
        self._requests: dict[str, ReviewRequest] = {}
        if self._path.exists():
            rows = json.loads(self._path.read_text(encoding="utf-8"))
            for row in rows:
                req = ReviewRequest.from_dict(row)
                self._requests[req.id] = req

    def _save(self) -> None:
        rows = [req.to_dict() for req in self._requests.values()]
        self._path.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    def create(self, **fields: Any) -> ReviewRequest:
        req_id = str(uuid.uuid4())
        req = ReviewRequest(
            id=req_id,
            workspace_id=fields.get("workspace_id", "default"),
            title=fields["title"],
            context_message=fields.get("context_message", ""),
            artifact_type=fields["artifact_type"],
            artifact_content=fields.get("artifact_content", ""),
            artifact_url=fields.get("artifact_url", ""),
            artifact_filename=fields.get("artifact_filename", ""),
            reviewer_name=fields["reviewer_name"],
            reviewer_email=fields["reviewer_email"],
            reviewer_webhook_url=fields.get("reviewer_webhook_url", ""),
            allowed_actions=list(fields.get("allowed_actions") or ["approve", "reject"]),
            token_id=fields["token_id"],
            expires_at=fields["expires_at"],
            reminder_at=fields.get("reminder_at"),
            status="pending",
            playbook_run_id=fields.get("playbook_run_id"),
            playbook_step_id=fields.get("playbook_step_id"),
            domain_pack=str(fields.get("domain_pack") or ""),
            created_at=_utcnow().isoformat(),
            created_by_user_id=fields.get("created_by_user_id"),
        )
        self._requests[req_id] = req
        self._save()
        return req

    def get(self, request_id: str) -> ReviewRequest | None:
        return self._requests.get(request_id)

    def get_by_token_id(self, token_id: str) -> ReviewRequest | None:
        for req in self._requests.values():
            if req.token_id == token_id:
                return req
        return None

    def list_for_workspace(
        self,
        workspace_id: str,
        *,
        status: str | None = None,
    ) -> list[ReviewRequest]:
        rows = [r for r in self._requests.values() if r.workspace_id == workspace_id]
        if status:
            rows = [r for r in rows if r.status == status]
        return sorted(rows, key=lambda r: r.created_at, reverse=True)

    def update(self, req: ReviewRequest) -> None:
        self._requests[req.id] = req
        self._save()

    def record_decision(
        self,
        req: ReviewRequest,
        *,
        action: str,
        reviewer_note: str,
        reviewer_ip_hash: str,
    ) -> ReviewDecision:
        decision = ReviewDecision(
            id=str(uuid.uuid4()),
            review_request_id=req.id,
            action=action,
            reviewer_note=reviewer_note,
            token_id=req.token_id,
            reviewer_ip_hash=reviewer_ip_hash,
            decided_at=_utcnow().isoformat(),
        )
        req.decision = decision
        req.status = "decided"
        self.update(req)
        return decision

    def expire_due(self) -> list[ReviewRequest]:
        now = _utcnow()
        expired: list[ReviewRequest] = []
        for req in self._requests.values():
            if req.status != "pending":
                continue
            expires = datetime.fromisoformat(req.expires_at)
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if now > expires:
                req.status = "expired"
                self.update(req)
                expired.append(req)
        return expired

    def due_reminders(self) -> list[ReviewRequest]:
        now = _utcnow()
        due: list[ReviewRequest] = []
        for req in self._requests.values():
            if req.status != "pending" or not req.reminder_at:
                continue
            reminder = datetime.fromisoformat(req.reminder_at)
            if reminder.tzinfo is None:
                reminder = reminder.replace(tzinfo=timezone.utc)
            if now >= reminder:
                due.append(req)
        return due


_store: ReviewStore | None = None


def get_review_store() -> ReviewStore:
    global _store
    if _store is None:
        _store = ReviewStore()
    return _store
