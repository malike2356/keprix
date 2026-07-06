"""Pack signature verification."""

from __future__ import annotations

from keprix.hub.manifests import PackManifest
from keprix.hub.package_signing import sign_package, verify_package


def sign_manifest(manifest: PackManifest) -> str:
    payload = manifest.to_dict()
    payload.pop("signature", None)
    return sign_package(manifest.name, manifest.version, payload)


def verify_manifest(manifest: PackManifest) -> bool:
    if not manifest.signature:
        return manifest.trust_label == "official"
    payload = manifest.to_dict()
    payload.pop("signature", None)
    return verify_package(manifest.name, manifest.version, payload, manifest.signature)
