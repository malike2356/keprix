"""Hard consent gate before user data enters AI models (granular, withdrawable)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from keprix.transparency.config import consent_required

AiFeature = Literal[
    "text_generation",
    "image_generation",
    "code_generation",
    "audio_generation",
    "video_generation",
    "embeddings",
]

AI_FEATURES: tuple[str, ...] = (
    "text_generation",
    "image_generation",
    "code_generation",
    "audio_generation",
    "video_generation",
    "embeddings",
)

ConsentAction = Literal["granted", "denied", "withdrawn"]


class ConsentRequiredError(PermissionError):
    """Raised when AI processing is attempted without affirmative consent."""

    def __init__(self, feature: str, user_id: str) -> None:
        self.feature = feature
        self.user_id = user_id
        super().__init__(
            f"AI consent required for feature '{feature}' before processing user input"
        )


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _default_dir() -> Path:
    try:
        from keprix_cli.config import get_keprix_home

        root = Path(get_keprix_home()) / "transparency"
    except Exception:
        root = Path.home() / ".keprix" / "transparency"
    root.mkdir(parents=True, exist_ok=True)
    return root


class ConsentGate:
    """Append-only consent ledger; withdrawal is a new entry, never a delete."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self._path = (base_dir or _default_dir()) / "ai_consent_log.jsonl"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text("", encoding="utf-8")

    def _append(self, row: dict[str, Any]) -> dict[str, Any]:
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        return row

    def _iter(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line in self._path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return rows

    def record_consent(
        self,
        user_id: str,
        feature: str,
        *,
        action: ConsentAction = "granted",
        affirmative: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        feature = str(feature).strip()
        if feature not in AI_FEATURES:
            raise ValueError(f"Unknown AI feature '{feature}'")
        if action == "granted" and not affirmative:
            raise ValueError("Consent grant requires affirmative=True (no pre-checked defaults)")
        row = {
            "id": str(uuid.uuid4()),
            "user_id": str(user_id),
            "feature": feature,
            "action": action,
            "affirmative": bool(affirmative),
            "timestamp": _utcnow(),
            "metadata": metadata or {},
        }
        return self._append(row)

    def get_consent_status(self, user_id: str) -> dict[str, Any]:
        latest: dict[str, dict[str, Any]] = {}
        for row in self._iter():
            if row.get("user_id") != user_id:
                continue
            feature = str(row.get("feature") or "")
            latest[feature] = row
        status: dict[str, str] = {}
        for feature in AI_FEATURES:
            row = latest.get(feature)
            if row is None:
                status[feature] = "missing"
            else:
                status[feature] = str(row.get("action") or "missing")
        return {
            "user_id": user_id,
            "features": status,
            "history": [r for r in self._iter() if r.get("user_id") == user_id],
        }

    def require_consent(self, user_id: str, feature: str) -> dict[str, Any]:
        if not consent_required():
            return {"ok": True, "skipped": True, "feature": feature}
        feature = str(feature).strip()
        if feature not in AI_FEATURES:
            raise ValueError(f"Unknown AI feature '{feature}'")
        status = self.get_consent_status(user_id)
        action = status["features"].get(feature, "missing")
        if action != "granted":
            raise ConsentRequiredError(feature, user_id)
        return {"ok": True, "feature": feature, "action": action}

    def consent_gate(self, feature: str):
        """Return a callable middleware that blocks until consent is recorded."""

        def _gate(user_id: str) -> dict[str, Any]:
            return self.require_consent(user_id, feature)

        return _gate

    def delete_consent(self, *_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError("AI consent log is append-only; use action=withdrawn instead")


_gate: ConsentGate | None = None


def get_consent_gate() -> ConsentGate:
    global _gate
    if _gate is None:
        _gate = ConsentGate()
    return _gate
