"""Multi-source context loading for coding chat sessions."""

from __future__ import annotations

import base64
import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from keprix.coding.voice_to_code import voice_to_coding_request
from keprix.security.redactor import get_redactor


@dataclass
class ContextArtifact:
    kind: str
    source: str
    summary: str
    content_hash: str
    redacted_preview: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class LoadedContext:
    artifacts: list[ContextArtifact] = field(default_factory=list)
    coding_request: str = ""

    def to_trace_payload(self) -> dict[str, Any]:
        return {
            "coding_request": self.coding_request,
            "artifacts": [
                {
                    "kind": item.kind,
                    "source": item.source,
                    "summary": item.summary,
                    "content_hash": item.content_hash,
                    "metadata": item.metadata,
                }
                for item in self.artifacts
            ],
        }


def load_context(
    *,
    repo_path: Path | None = None,
    files: list[str] | None = None,
    urls: list[str] | None = None,
    images: list[str] | None = None,
    voice_transcript: str | None = None,
    clipboard_text: str | None = None,
    issue_text: str | None = None,
) -> LoadedContext:
    redactor = get_redactor()
    artifacts: list[ContextArtifact] = []
    request_parts: list[str] = []

    if issue_text:
        request_parts.append(issue_text.strip())

    if voice_transcript:
        normalized = voice_to_coding_request(voice_transcript)
        artifacts.append(_artifact("voice", "microphone", normalized, redactor))
        request_parts.append(normalized)

    if clipboard_text:
        artifacts.append(_artifact("clipboard", "clipboard", clipboard_text, redactor))
        if not request_parts:
            request_parts.append(clipboard_text.strip())

    root = repo_path.resolve() if repo_path else None
    for rel in files or []:
        if root is None:
            continue
        path = (root / rel).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            continue
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")[:12000]
        artifacts.append(_artifact("file", rel, text, redactor, metadata={"size": path.stat().st_size}))

    for url in urls or []:
        artifacts.append(_url_artifact(url, redactor))

    for image_ref in images or []:
        artifacts.append(_image_artifact(image_ref, redactor))

    coding_request = "\n\n".join(part for part in request_parts if part).strip()
    return LoadedContext(artifacts=artifacts, coding_request=coding_request)


def _artifact(kind: str, source: str, content: str, redactor: Any, metadata: dict[str, Any] | None = None) -> ContextArtifact:
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    preview = redactor.redact(content[:2000])
    summary = preview.splitlines()[0][:160] if preview else ""
    return ContextArtifact(
        kind=kind,
        source=source,
        summary=summary,
        content_hash=digest,
        redacted_preview=preview,
        metadata=metadata or {},
    )


def _url_artifact(url: str, redactor: Any) -> ContextArtifact:
    parsed = urlparse(url)
    content = f"URL reference: {url}\nHost: {parsed.netloc}\nPath: {parsed.path}"
    return _artifact("url", url, content, redactor, metadata={"scheme": parsed.scheme})


def _image_artifact(image_ref: str, redactor: Any) -> ContextArtifact:
    path = Path(image_ref)
    metadata: dict[str, Any] = {"reference": image_ref}
    content = f"Image reference: {image_ref}"
    if path.is_file():
        raw = path.read_bytes()[:500_000]
        metadata["mime_guess"] = _guess_image_mime(path.suffix)
        metadata["bytes"] = len(raw)
        content = f"Image file: {path.name}\nsha256={hashlib.sha256(raw).hexdigest()}"
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
            metadata["data_url_prefix"] = f"data:{metadata['mime_guess']};base64,"
            metadata["base64_preview"] = base64.b64encode(raw[:4096]).decode("ascii")
    return _artifact("image", image_ref, content, redactor, metadata=metadata)


def _guess_image_mime(suffix: str) -> str:
    mapping = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    return mapping.get(suffix.lower(), "application/octet-stream")


def save_trace_bundle(context: LoadedContext, run_id: str) -> Path:
    base = Path.home() / ".keprix" / "workspace" / "coding-context"
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"{run_id}.json"
    payload = {
        "saved_at": datetime.now(timezone.utc).isoformat(),
        **context.to_trace_payload(),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
