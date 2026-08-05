"""HTTP routes exposing the shared UI contract."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends

from keprix.auth.dependencies import get_current_user
from keprix.ui_contract import build_ui_contract
from keprix.ui_contract.navigation import navigation_for_role

router = APIRouter(prefix="/api/ui", tags=["ui-contract"])


@router.get("/contract")
async def get_ui_contract(user: dict = Depends(get_current_user)) -> dict:
    return build_ui_contract(user)


@router.get("/module-inventory")
async def get_module_inventory(user: dict = Depends(get_current_user)) -> dict:
    role = str(user.get("role") or "user")
    repo = Path(__file__).resolve().parents[3]
    nav = navigation_for_role(role)
    linked_paths = {str(item.get("href") or "").rstrip("/") or "/" for item in nav.get("items", [])}

    workspace_pages = []
    app_root = repo / "frontend" / "src" / "app" / "(workspace)"
    if app_root.exists():
        for page in sorted(app_root.rglob("page.tsx")):
            rel = page.relative_to(app_root).parent
            route = "/" + "/".join(part for part in rel.parts if part)
            if route == "/.":
                route = "/"
            route = route.rstrip("/") or "/"
            dynamic = "[" in route or "]" in route
            workspace_pages.append(
                {
                    "route": route,
                    "file": str(page.relative_to(repo)),
                    "linked": route in linked_paths,
                    "dynamic": dynamic,
                }
            )

    api_modules = []
    api_root = repo / "src" / "keprix" / "api"
    if api_root.exists():
        for path in sorted(api_root.glob("*.py")):
            if path.name in {"__init__.py", "server.py"}:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if "APIRouter" not in text and "@router." not in text:
                continue
            route_count = text.count("@router.")
            api_modules.append(
                {
                    "module": path.stem,
                    "file": str(path.relative_to(repo)),
                    "route_count": route_count,
                }
            )

    unlinked_pages = [page for page in workspace_pages if not page["linked"] and not page["dynamic"]]
    return {
        "navigation_count": len(linked_paths),
        "workspace_page_count": len(workspace_pages),
        "unlinked_workspace_page_count": len(unlinked_pages),
        "api_module_count": len(api_modules),
        "unlinked_workspace_pages": unlinked_pages,
        "workspace_pages": workspace_pages,
        "api_modules": api_modules,
    }
