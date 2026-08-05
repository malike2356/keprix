#!/usr/bin/env python3
"""CLI wrapper for Keprix video ingest."""

from __future__ import annotations

import argparse
import json

from keprix.ingest.video_ingest_service import VideoIngestService


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest a video into transcript/frame manifest form")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--url")
    source.add_argument("--file")
    parser.add_argument("--mode", choices=["caption-only", "sparse", "balanced", "dense"], default="balanced")
    parser.add_argument("--copy-to-vault", action="store_true")
    parser.add_argument("--sparse-minutes", type=int, default=5)
    parser.add_argument("--dense-interval-sec", type=int, default=30)
    parser.add_argument("--max-frames", type=int, default=None)
    args = parser.parse_args()

    job = VideoIngestService().ingest(
        args.url or args.file,
        mode=args.mode,
        copy_to_vault=args.copy_to_vault,
        sparse_minutes=args.sparse_minutes,
        dense_interval_sec=args.dense_interval_sec,
        max_frames=args.max_frames,
    )
    print(json.dumps(job.to_dict(), indent=2))
    return 0 if job.status == "done" else 1


if __name__ == "__main__":
    raise SystemExit(main())
