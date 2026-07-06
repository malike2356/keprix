"""Localization CLI subcommand parsers."""

from __future__ import annotations

from typing import Callable


def build_language_parser(
    subparsers,
    *,
    cmd_detect: Callable,
    cmd_translate: Callable,
    cmd_transcribe: Callable,
    cmd_flywheel_export: Callable | None = None,
) -> None:
    language_parser = subparsers.add_parser(
        "language",
        help="Detect, translate, and transcribe text",
        description="Localization utilities for African language workflows.",
    )
    language_sub = language_parser.add_subparsers(dest="language_command", required=True)

    detect_parser = language_sub.add_parser("detect", help="Detect language from text")
    detect_parser.add_argument("text", help="Text to analyze")
    detect_parser.add_argument("--hint", default=None, help="Optional BCP 47 hint")
    detect_parser.set_defaults(func=cmd_detect)

    translate_parser = language_sub.add_parser("translate", help="Translate text")
    translate_parser.add_argument("text", help="Text to translate")
    translate_parser.add_argument("--source", default=None, help="Source BCP 47 code")
    translate_parser.add_argument("--target", required=True, help="Target BCP 47 code")
    translate_parser.add_argument("--workspace-id", default="default")
    translate_parser.add_argument("--glossary-id", default=None)
    translate_parser.add_argument("--verbose", action="store_true")
    translate_parser.set_defaults(func=cmd_translate)

    transcribe_parser = language_sub.add_parser("transcribe", help="Transcribe audio file")
    transcribe_parser.add_argument("audio", help="Path to audio file")
    transcribe_parser.add_argument("--source", default=None, help="Source BCP 47 code")
    transcribe_parser.add_argument("--target", default="en")
    transcribe_parser.add_argument("--verbose", action="store_true")
    transcribe_parser.set_defaults(func=cmd_transcribe)

    if cmd_flywheel_export is not None:
        flywheel = language_sub.add_parser("flywheel-export", help="Export SM4T/LLM training data")
        flywheel.add_argument("output", help="Output directory")
        flywheel.add_argument("--workspace-id", default="default")
        flywheel.add_argument("--domain", default=None)
        flywheel.add_argument("--task-type", default=None, choices=["s2t", "t2t"])
        flywheel.add_argument("--min-quality", type=int, default=3)
        flywheel.add_argument("--since", default=None, help="ISO8601 timestamp")
        flywheel.set_defaults(func=cmd_flywheel_export)
