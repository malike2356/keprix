"""Hub manifest tests."""

from __future__ import annotations

from keprix.hub.manifests import PackManifest, validate_manifest


def test_valid_manifest_passes() -> None:
    manifest = PackManifest(
        name="demo",
        version="1.0.0",
        type="skill_pack",
        author="test",
        license="MIT",
        files=["skills/demo/SKILL.md"],
        uninstall_plan=["remove skills/demo"],
    )
    assert validate_manifest(manifest) == []


def test_invalid_manifest_fails() -> None:
    manifest = PackManifest(
        name="",
        version="",
        type="unknown",
        author="test",
        license="MIT",
        files=[],
        uninstall_plan=[],
    )
    errors = validate_manifest(manifest)
    assert errors
