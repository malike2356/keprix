"""Ingest CLI parser."""

from __future__ import annotations

from argparse import _SubParsersAction
from collections.abc import Callable


def build_ingest_parser(
    subparsers: _SubParsersAction,
    *,
    cmd_video: Callable,
) -> None:
    parser = subparsers.add_parser("ingest", help="Ingest external media and artifacts")
    sub = parser.add_subparsers(dest="ingest_command", required=True)

    video = sub.add_parser("video", help="Ingest a YouTube, remote, or local video")
    video.add_argument("video_action", nargs="?", choices=["list", "show"], help="List jobs or show one job")
    video.add_argument("job_id", nargs="?", help="Job id for `show`")
    source = video.add_mutually_exclusive_group(required=False)
    source.add_argument("--url", help="YouTube or direct video URL")
    source.add_argument("--file", help="Local MP4, MOV, or WebM path")
    video.add_argument("--mode", choices=["caption-only", "sparse", "balanced", "dense"], default="balanced")
    video.add_argument("--copy-to-vault", action="store_true")
    video.add_argument("--sparse-minutes", type=int, default=5)
    video.add_argument("--dense-interval-sec", type=int, default=30)
    video.add_argument("--max-frames", type=int, default=None)
    video.add_argument("--limit", type=int, default=20, help="List limit")
    video.set_defaults(func=cmd_video)
