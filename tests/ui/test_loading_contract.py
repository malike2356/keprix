"""Frontend loading-state contract (static analysis).

Guards against regressions to plain ``Loading...`` copy or page-level spinners in
workspace/admin routes. Button spinners and a small allowlist are permitted.

Allowlist (extend only with a linked issue):

- ``chat/page.tsx``: session bootstrap spinner
- ``chat/[sessionId]/page.tsx``: reserved for session bootstrap if added
- ``analytics/page.tsx``: file upload busy indicator
- ``components/ui/DataTable.tsx``: secondary table actions may use spinners
- Form submit handlers inside dialogs (not scanned as page files)
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend" / "src"
LOADING_INDEX = FRONTEND / "components" / "ui" / "loading" / "index.ts"

LOADING_TEXT_RE = re.compile(r"Loading [a-z]+\.\.\.")
CIRCULAR_PROGRESS_IMPORT_RE = re.compile(
    r'import\s+CircularProgress\s+from\s+"@mui/material/CircularProgress"'
)
LOADING_CONTRACT_IGNORE = "@loading-contract-ignore"

LOADING_TEXT_ALLOWLIST = {
    FRONTEND / "app" / "(workspace)" / "chat" / "page.tsx",
    FRONTEND / "app" / "(workspace)" / "chat" / "[sessionId]" / "page.tsx",
}

CIRCULAR_PROGRESS_PAGE_ALLOWLIST = {
    FRONTEND / "app" / "(workspace)" / "chat" / "page.tsx",
    FRONTEND / "app" / "(workspace)" / "chat" / "[sessionId]" / "page.tsx",
    FRONTEND / "app" / "(workspace)" / "analytics" / "page.tsx",
}

CIRCULAR_PROGRESS_COMPONENT_ALLOWLIST = {
    FRONTEND / "components" / "ui" / "DataTable.tsx",
}


def _page_files() -> list[Path]:
    paths: list[Path] = []
    for base in (
        FRONTEND / "app" / "(workspace)",
        FRONTEND / "app" / "(admin)",
    ):
        if base.is_dir():
            paths.extend(sorted(base.rglob("page.tsx")))
    return paths


def _component_files() -> list[Path]:
    base = FRONTEND / "components"
    return sorted(base.rglob("*.tsx")) if base.is_dir() else []


def test_loading_module_exports_primitives():
    assert LOADING_INDEX.is_file()
    text = LOADING_INDEX.read_text(encoding="utf-8")
    for symbol in ("AsyncView", "SkeletonTable", "SkeletonList"):
        assert symbol in text


def test_no_plain_loading_text_in_workspace_components():
    violations: list[str] = []
    for path in _component_files():
        if "components/ui/loading/" in path.as_posix():
            continue
        if path in LOADING_TEXT_ALLOWLIST:
            continue
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if LOADING_TEXT_RE.search(line):
                violations.append(f"{path.relative_to(ROOT)}:{line_no}: {line.strip()}")
    assert not violations, "Use skeleton primitives instead of Loading... text:\n" + "\n".join(
        violations
    )


def test_no_plain_loading_text_in_workspace_pages():
    violations: list[str] = []
    for path in _page_files():
        if path in LOADING_TEXT_ALLOWLIST:
            continue
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if LOADING_TEXT_RE.search(line):
                violations.append(f"{path.relative_to(ROOT)}:{line_no}: {line.strip()}")
    assert not violations, "Use skeleton primitives instead of Loading... text:\n" + "\n".join(
        violations
    )


def test_no_inline_mui_skeleton_outside_loading_module():
    violations: list[str] = []
    for path in sorted(FRONTEND.rglob("*.tsx")):
        if "components/ui/loading/" in path.as_posix():
            continue
        text = path.read_text(encoding="utf-8")
        if 'from "@mui/material/Skeleton"' in text:
            violations.append(str(path.relative_to(ROOT)))
    assert not violations, "Import skeleton primitives from @/components/ui/loading:\n" + "\n".join(
        violations
    )


@pytest.mark.parametrize("path", _page_files(), ids=lambda p: p.relative_to(FRONTEND).as_posix())
def test_workspace_admin_pages_avoid_circular_progress(path: Path):
    if path in CIRCULAR_PROGRESS_PAGE_ALLOWLIST:
        return
    text = path.read_text(encoding="utf-8")
    if not CIRCULAR_PROGRESS_IMPORT_RE.search(text):
        return
    for line_no, line in enumerate(text.splitlines(), start=1):
        if CIRCULAR_PROGRESS_IMPORT_RE.search(line):
            if LOADING_CONTRACT_IGNORE not in line:
                pytest.fail(
                    f"{path.relative_to(ROOT)}:{line_no}: page-level CircularProgress is not allowed; "
                    "use @/components/ui/loading primitives or add @loading-contract-ignore with justification"
                )


def test_component_circular_progress_is_allowlisted_or_ignored():
    violations: list[str] = []
    for path in _component_files():
        if path in CIRCULAR_PROGRESS_COMPONENT_ALLOWLIST:
            continue
        if "components/ui/loading/" in path.as_posix():
            continue
        text = path.read_text(encoding="utf-8")
        if not CIRCULAR_PROGRESS_IMPORT_RE.search(text):
            continue
        if LOADING_CONTRACT_IGNORE in text:
            continue
        violations.append(str(path.relative_to(ROOT)))
    assert not violations, (
        "CircularProgress in components must be button-only spinners with "
        "@loading-contract-ignore or be added to the allowlist:\n" + "\n".join(violations)
    )
