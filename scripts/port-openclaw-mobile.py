#!/usr/bin/env python3
"""Port OpenClaw iOS/Android/macos/shared kit to keprix/mobile with Carina renames."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "planning/competitor-research/agents-to-adopt/openclaw/apps"
DEST = ROOT / "mobile"

COPY_MAP = {
    "ios": SRC / "ios",
    "android": SRC / "android",
    "macos": SRC / "macos",
    "shared/CarinaKit": SRC / "shared/OpenClawKit",
    "swabble": SRC / "swabble",
}

TEXT_SUFFIXES = {
    ".swift",
    ".kt",
    ".kts",
    ".gradle",
    ".properties",
    ".xml",
    ".yml",
    ".yaml",
    ".json",
    ".md",
    ".txt",
    ".xcconfig",
    ".plist",
    ".pro",
    ".toml",
    ".html",
    ".sh",
    ".ts",
    ".input",
    ".xcfilelist",
    ".example",
}

REPLACEMENTS = [
    ("OpenClawChatUI", "CarinaChatUI"),
    ("OpenClawProtocol", "CarinaProtocol"),
    ("OpenClawKit", "CarinaKit"),
    ("OpenClaw", "Carina"),
    ("openclawfoundation", "verlox.carinakeprix"),
    ("ai.openclaw", "com.verlox.carinakeprix"),
    ("com.openclaw", "com.verlox.carinakeprix"),
    ("https://ios-push-relay.openclaw.ai", "{serverURL}/api/notifications/push"),
    ("https://docs.openclaw.ai", "https://docs.keprix.local"),
    ("https://openclaw.ai", "https://keprix.local"),
    ("openclaw.ai", "keprix.local"),
    ("support@openclaw.ai", "support@keprix.local"),
]


def rename_paths(base: Path) -> None:
    for path in sorted(base.rglob("*"), reverse=True):
        name = path.name
        new_name = name.replace("OpenClaw", "Carina")
        if new_name != name:
            path.rename(path.with_name(new_name))


def rewrite_file(path: Path) -> None:
    if path.suffix not in TEXT_SUFFIXES and path.name not in {"gradlew", "Appfile", "Fastfile"}:
        return
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return
    original = text
    for old, new in REPLACEMENTS:
        text = text.replace(old, new)
    if text != original:
        path.write_text(text, encoding="utf-8")


def move_android_package(base: Path) -> None:
    old = base / "android/app/src/main/java/ai/openclaw/android"
    new = base / "android/app/src/main/java/com/verlox/carinakeprix"
    if old.exists():
        new.parent.mkdir(parents=True, exist_ok=True)
        if new.exists():
            shutil.rmtree(new)
        shutil.move(str(old), str(new))
    for flavor in ("test", "testThirdParty", "play", "thirdParty"):
        old_test = base / f"android/app/src/{flavor}/java/ai/openclaw/android"
        new_test = base / f"android/app/src/{flavor}/java/com/verlox/carinakeprix"
        if old_test.exists():
            new_test.parent.mkdir(parents=True, exist_ok=True)
            if new_test.exists():
                shutil.rmtree(new_test)
            shutil.move(str(old_test), str(new_test))
    benchmark_old = base / "android/benchmark/src/main/java/ai/openclaw/app"
    benchmark_new = base / "android/benchmark/src/main/java/com/verlox/carinakeprix"
    if benchmark_old.exists():
        benchmark_new.parent.mkdir(parents=True, exist_ok=True)
        if benchmark_new.exists():
            shutil.rmtree(benchmark_new)
        shutil.move(str(benchmark_old), str(benchmark_new))


def main() -> None:
    if DEST.exists():
        shutil.rmtree(DEST)
    DEST.mkdir(parents=True)
    for dest_name, src_path in COPY_MAP.items():
        target = DEST / dest_name
        if not src_path.exists():
            print(f"skip missing {src_path}")
            continue
        shutil.copytree(src_path, target)
        print(f"copied {src_path} -> {target}")

    rename_paths(DEST)
    for path in DEST.rglob("*"):
        if path.is_file():
            rewrite_file(path)

    move_android_package(DEST)

    ios_project = DEST / "ios/project.yml"
    if ios_project.exists():
        text = ios_project.read_text(encoding="utf-8")
        text = text.replace("../shared/CarinaKit", "../shared/CarinaKit")
        text = text.replace("name: Carina", "name: keprix")
        text = re.sub(r"bundleIdPrefix: .*", "bundleIdPrefix: com.verlox", text)
        ios_project.write_text(text, encoding="utf-8")

    signing = DEST / "ios/Config/Signing.xcconfig"
    if not signing.exists():
        signing.parent.mkdir(parents=True, exist_ok=True)
        signing.write_text(
            "PRODUCT_BUNDLE_IDENTIFIER = com.verlox.carinakeprix\nDEVELOPMENT_TEAM = \n",
            encoding="utf-8",
        )

    print("port complete")


if __name__ == "__main__":
    main()
