from __future__ import annotations

from pathlib import Path

import pytest

from keprix.release_manifest import artifact_record, build_manifest, dumps, validate_manifest


def artifact(tmp_path: Path) -> dict[str, object]:
    path = tmp_path / "keprix-0.16.0-linux-amd64.whl"
    path.write_bytes(b"release bytes")
    return artifact_record(
        path,
        base_url="https://github.com/malike2356/keprix/releases/download/v0.16.0",
        kind="wheel",
        platform="linux",
        arch="amd64",
    )


def test_build_manifest_is_valid_and_deterministic(tmp_path: Path) -> None:
    record = artifact(tmp_path)
    manifest = build_manifest(
        version="0.16.0",
        commit="a" * 40,
        tag="v0.16.0",
        channel="stable",
        artifacts=[record],
        built_at="2026-08-08T12:00:00+00:00",
    )
    assert validate_manifest(manifest) == []
    assert dumps(manifest) == dumps(manifest)
    assert manifest["artifacts"][0]["sha256"]


def test_stable_manifest_rejects_mutable_main_url(tmp_path: Path) -> None:
    record = artifact(tmp_path)
    record["url"] = "https://raw.githubusercontent.com/malike2356/keprix/main/file.whl"
    with pytest.raises(ValueError, match="immutable HTTPS"):
        build_manifest(
            version="0.16.0",
            commit="b" * 40,
            tag="v0.16.0",
            channel="stable",
            artifacts=[record],
        )


def test_manifest_rejects_duplicate_artifacts(tmp_path: Path) -> None:
    record = artifact(tmp_path)
    errors = validate_manifest(
        {
            "schema": "keprix.release-manifest.v1",
            "version": "0.16.0",
            "channel": "beta",
            "git_commit": "c" * 40,
            "artifacts": [record, record],
        }
    )
    assert "artifacts[1].id must be unique" in errors
