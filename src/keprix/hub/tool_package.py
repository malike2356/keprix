"""Shareable signed tool packages for the Keprix hub."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from keprix.hub.package_signing import sign_package, verify_package


@dataclass
class ToolPackage:
    name: str
    version: str
    description: str
    tools: list[dict]
    signature: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "tools": self.tools,
            "signature": self.signature,
        }


def build_tool_package(name: str, version: str, description: str, tools: list[dict]) -> ToolPackage:
    manifest = {"type": "tool", "tools": tools}
    signature = sign_package(name, version, manifest)
    return ToolPackage(name=name, version=version, description=description, tools=tools, signature=signature)


def save_tool_package(package: ToolPackage, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    package_dir = output_dir / package.name
    if package_dir.exists():
        shutil.rmtree(package_dir)
    package_dir.mkdir()
    (package_dir / "tool-package.json").write_text(json.dumps(package.to_dict(), indent=2), encoding="utf-8")
    return package_dir


def load_tool_package(package_dir: Path) -> ToolPackage:
    manifest_path = package_dir / "tool-package.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"missing tool-package.json in {package_dir}")
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    return ToolPackage(
        name=data["name"],
        version=data["version"],
        description=data.get("description", ""),
        tools=data.get("tools", []),
        signature=data.get("signature", ""),
    )


def verify_tool_package(package: ToolPackage) -> bool:
    if not package.signature:
        return False
    manifest = {"type": "tool", "tools": package.tools}
    return verify_package(package.name, package.version, manifest, package.signature)


def install_tool_package(package_dir: Path, *, require_verified: bool = True) -> ToolPackage:
    package = load_tool_package(package_dir)
    if require_verified and not verify_tool_package(package):
        raise ValueError("tool package signature verification failed")
    install_root = Path.home() / ".keprix" / "hub" / "tools" / package.name
    install_root.mkdir(parents=True, exist_ok=True)
    shutil.copytree(package_dir, install_root, dirs_exist_ok=True)
    return package
