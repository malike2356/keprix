"""Shareable signed agent packages for the Keprix hub."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from keprix.hub.package_signing import sign_package, verify_package


@dataclass
class AgentPackage:
    name: str
    version: str
    description: str
    manifest: dict
    signature: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "manifest": self.manifest,
            "signature": self.signature,
        }


def build_agent_package(
    name: str,
    version: str,
    description: str,
    *,
    system_prompt: str,
    tools: list[str],
    modalities: list[str] | None = None,
) -> AgentPackage:
    manifest = {
        "type": "agent",
        "system_prompt": system_prompt,
        "tools": tools,
        "modalities": modalities or ["text", "file", "url"],
    }
    signature = sign_package(name, version, manifest)
    return AgentPackage(name=name, version=version, description=description, manifest=manifest, signature=signature)


def save_agent_package(package: AgentPackage, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    package_dir = output_dir / package.name
    if package_dir.exists():
        shutil.rmtree(package_dir)
    package_dir.mkdir()
    (package_dir / "agent-package.json").write_text(json.dumps(package.to_dict(), indent=2), encoding="utf-8")
    return package_dir


def load_agent_package(package_dir: Path) -> AgentPackage:
    manifest_path = package_dir / "agent-package.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"missing agent-package.json in {package_dir}")
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    return AgentPackage(
        name=data["name"],
        version=data["version"],
        description=data.get("description", ""),
        manifest=data.get("manifest", {}),
        signature=data.get("signature", ""),
    )


def verify_agent_package(package: AgentPackage) -> bool:
    if not package.signature:
        return False
    return verify_package(package.name, package.version, package.manifest, package.signature)


def install_agent_package(package_dir: Path, *, require_verified: bool = True) -> AgentPackage:
    package = load_agent_package(package_dir)
    if require_verified and not verify_agent_package(package):
        raise ValueError("agent package signature verification failed")
    install_root = Path.home() / ".keprix" / "hub" / "agents" / package.name
    install_root.mkdir(parents=True, exist_ok=True)
    shutil.copytree(package_dir, install_root, dirs_exist_ok=True)
    return package
