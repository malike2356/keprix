"""CLI handlers for localization commands."""

from __future__ import annotations

import asyncio
import base64
import json
import sys
from pathlib import Path


def _run(coro):
    return asyncio.run(coro)


def cmd_language_detect(args) -> int:
    from keprix.backend.localization.detection import detect_language

    result = _run(detect_language(args.text, hint=args.hint))
    payload = {
        "language_code": result.language_code,
        "language_name": result.language_name,
        "confidence": result.confidence,
        "provider": result.provider,
    }
    print(json.dumps(payload, indent=2))
    return 0


def cmd_language_translate(args) -> int:
    from keprix.backend.localization.translation import translate_text

    result = _run(
        translate_text(
            workspace_id=args.workspace_id,
            text=args.text,
            source_language=args.source,
            target_language=args.target,
            glossary_id=args.glossary_id,
        )
    )
    print(result.translated_text)
    if args.verbose:
        print(json.dumps(result.__dict__, indent=2, default=str), file=sys.stderr)
    return 0


def cmd_language_transcribe(args) -> int:
    from keprix.backend.localization.transcription import transcribe_audio

    audio_path = Path(args.audio)
    audio = audio_path.read_bytes()
    result = _run(
        transcribe_audio(
            audio,
            source_language=args.source,
            target_language=args.target,
        )
    )
    print(result.transcript)
    if args.verbose:
        print(json.dumps(result.__dict__, indent=2, default=str), file=sys.stderr)
    return 0


def cmd_language_flywheel_export(args) -> int:
    from datetime import datetime

    from keprix.backend.localization.flywheel import get_flywheel

    since = datetime.fromisoformat(args.since.replace("Z", "+00:00")) if args.since else None
    summary = _run(
        get_flywheel().export_sm4t_training_data(
            Path(args.output),
            workspace_id=args.workspace_id,
            domain=args.domain,
            task_type=args.task_type,
            min_quality_score=args.min_quality,
            since=since,
        )
    )
    llm = _run(
        get_flywheel().export_llm_correction_data(
            Path(args.output),
            workspace_id=args.workspace_id,
            domain=args.domain,
            since=since,
        )
    )
    payload = {"sm4t": summary.__dict__, "llm": llm}
    print(json.dumps(payload, indent=2))
    return 0
