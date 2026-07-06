"""Modality-agnostic input normalization for code agents."""

from __future__ import annotations

import base64
import hashlib
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from keprix.security.redactor import get_redactor


@dataclass
class ArtifactRef:
    ref_id: str
    kind: str
    source: str
    content_hash: str
    summary: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ModalityBundle:
    artifacts: list[ArtifactRef] = field(default_factory=list)
    primary_text: str = ""

    def to_prompt_context(self) -> str:
        lines = [self.primary_text] if self.primary_text else []
        for artifact in self.artifacts:
            lines.append(f"[{artifact.kind}:{artifact.ref_id}] {artifact.summary}")
        return "\n".join(line for line in lines if line).strip()


def normalize_inputs(
    *,
    text: str | None = None,
    image_paths: list[str] | None = None,
    audio_transcript: str | None = None,
    video_summary: str | None = None,
    file_paths: list[str] | None = None,
    urls: list[str] | None = None,
) -> ModalityBundle:
    redactor = get_redactor()
    artifacts: list[ArtifactRef] = []
    text_parts: list[str] = []

    if text:
        text_parts.append(redactor.redact(text.strip()))

    if audio_transcript:
        artifacts.append(_text_artifact("audio_transcript", "microphone", redactor.redact(audio_transcript.strip())))

    if video_summary:
        artifacts.append(_text_artifact("video_summary", "video", redactor.redact(video_summary.strip())))

    for path_str in file_paths or []:
        path = Path(path_str)
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8", errors="ignore")[:12000]
        artifacts.append(
            _text_artifact(
                "file",
                str(path),
                redactor.redact(content),
                metadata={"size": path.stat().st_size},
            )
        )

    for path_str in image_paths or []:
        path = Path(path_str)
        metadata: dict[str, Any] = {"reference": str(path)}
        digest = hashlib.sha256(path_str.encode("utf-8")).hexdigest()
        if path.is_file():
            raw = path.read_bytes()[:500_000]
            digest = hashlib.sha256(raw).hexdigest()
            metadata["bytes"] = len(raw)
            metadata["preview_base64"] = base64.b64encode(raw[:2048]).decode("ascii")
        artifacts.append(
            ArtifactRef(
                ref_id=_ref_id(),
                kind="image",
                source=str(path),
                content_hash=digest,
                summary=f"Image artifact {path.name}",
                metadata=metadata,
            )
        )

    for url in urls or []:
        parsed = urlparse(url)
        artifacts.append(
            ArtifactRef(
                ref_id=_ref_id(),
                kind="url",
                source=url,
                content_hash=hashlib.sha256(url.encode("utf-8")).hexdigest(),
                summary=f"URL {parsed.netloc}{parsed.path}",
                metadata={"scheme": parsed.scheme},
            )
        )

    return ModalityBundle(artifacts=artifacts, primary_text="\n\n".join(text_parts))


def _ref_id() -> str:
    return str(uuid.uuid4())


def _text_artifact(kind: str, source: str, content: str, metadata: dict[str, Any] | None = None) -> ArtifactRef:
    summary = content.splitlines()[0][:160] if content else ""
    return ArtifactRef(
        ref_id=_ref_id(),
        kind=kind,
        source=source,
        content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
        summary=summary,
        metadata=metadata or {},
    )
