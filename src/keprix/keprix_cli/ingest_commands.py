"""Ingest CLI command handlers."""

from __future__ import annotations

import json

from keprix.ingest.video_ingest_service import VideoIngestService


def cmd_ingest_video(args) -> int:
    if args.video_action == "list":
        return cmd_ingest_video_list(args)
    if args.video_action == "show":
        return cmd_ingest_video_show(args)
    source = args.url or args.file
    if not source:
        print(json.dumps({"error": "video ingest requires --url or --file"}))
        return 2
    job = VideoIngestService().ingest(
        source,
        mode=args.mode,
        copy_to_vault=args.copy_to_vault,
        sparse_minutes=args.sparse_minutes,
        dense_interval_sec=args.dense_interval_sec,
        max_frames=args.max_frames,
    )
    print(json.dumps(job.to_dict(), indent=2))
    return 0 if job.status == "done" else 1


def cmd_ingest_video_list(args) -> int:
    jobs = [job.to_dict() for job in VideoIngestService().store.list(limit=args.limit)]
    print(json.dumps({"jobs": jobs}, indent=2))
    return 0


def cmd_ingest_video_show(args) -> int:
    if not args.job_id:
        print(json.dumps({"error": "`keprix ingest video show` requires a job id"}))
        return 2
    job = VideoIngestService().store.get(args.job_id)
    if job is None:
        print(json.dumps({"error": "video ingest job not found"}))
        return 1
    print(json.dumps(job.to_dict(), indent=2))
    return 0
