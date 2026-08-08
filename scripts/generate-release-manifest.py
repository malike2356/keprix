#!/usr/bin/env python3
"""Build a signed-release manifest from an artifact directory."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from keprix.release_manifest import artifact_record, build_manifest, dumps


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--channel", choices=("stable", "beta"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    metadata = json.loads(args.metadata.read_text(encoding="utf-8"))
    records = []
    for item in metadata:
        path = args.artifacts / item["filename"]
        if not path.is_file():
            raise SystemExit(f"missing artifact: {path}")
        records.append(artifact_record(path, base_url=args.base_url, kind=item["kind"], platform=item["platform"], arch=item["architecture"]))
    manifest = build_manifest(version=args.version, commit=args.commit, tag=args.tag, channel=args.channel, artifacts=records)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(dumps(manifest), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
