"""Path-safe HTML preview and selection helpers."""

from __future__ import annotations

import html
import os
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from keprix.backend.builder.registry import get_project_registry
from keprix_constants import get_config_path, get_keprix_home
from keprix.design.preview_session_store import PreviewSession


def design_preview_enabled() -> bool:
    env = os.getenv("KEPRIX_DESIGN_PREVIEW_ENABLED")
    if env is not None:
        return env.strip().lower() not in {"0", "false", "no"}
    try:
        import yaml

        data = yaml.safe_load(Path(get_config_path()).read_text(encoding="utf-8")) or {}
        value = ((data.get("design") or {}).get("preview") or {}).get("enabled")
        if value is not None:
            return str(value).strip().lower() not in {"0", "false", "no"}
    except Exception:
        pass
    return True


def workspace_roots() -> list[Path]:
    roots: list[Path] = []
    env_root = os.getenv("KEPRIX_WORKSPACE_ROOT", "").strip()
    if env_root:
        roots.append(Path(env_root))
    roots.append(Path.cwd())
    try:
        roots.extend(Path(row["path"]) for row in get_project_registry().list_projects() if row.get("path"))
    except Exception:
        pass
    return _dedupe_resolved(roots)


def _dedupe_resolved(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    result: list[Path] = []
    for path in paths:
        try:
            resolved = path.expanduser().resolve()
        except OSError:
            continue
        key = str(resolved)
        if key not in seen:
            seen.add(key)
            result.append(resolved)
    return result


def _within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def resolve_preview_entry(path: str | None, artifact_id: str | None, entry: str | None = None) -> tuple[Path, Path]:
    if artifact_id:
        artifact_root = (get_keprix_home() / "design" / "artifacts" / artifact_id).resolve()
        entry_file = entry or "index.html"
        target = (artifact_root / entry_file).resolve()
        if not _within(target, artifact_root):
            raise HTTPException(status_code=403, detail="Preview entry escapes artifact root")
        if not target.is_file():
            raise HTTPException(status_code=404, detail="Preview artifact entry not found")
        return artifact_root, target

    if not path:
        raise HTTPException(status_code=422, detail="path or artifact_id is required")
    candidate = Path(path).expanduser()
    if candidate.is_dir():
        root = candidate.resolve()
        target = (root / (entry or "index.html")).resolve()
    else:
        target = candidate.resolve()
        root = target.parent
    if not any(_within(target, root_path) for root_path in workspace_roots()):
        raise HTTPException(status_code=403, detail="Preview path must be inside a workspace root")
    if not target.is_file():
        raise HTTPException(status_code=404, detail="Preview entry not found")
    if target.suffix.lower() not in {".html", ".htm"}:
        raise HTTPException(status_code=422, detail="Preview entry must be an HTML file")
    return root, target


def resolve_session_file(session: PreviewSession, relative_path: str = "") -> Path:
    root = Path(session.root_path or "").resolve()
    target = (root / relative_path).resolve() if relative_path else (root / session.entry_file).resolve()
    if not _within(target, root):
        raise HTTPException(status_code=403, detail="Preview asset escapes session root")
    if not target.is_file():
        raise HTTPException(status_code=404, detail="Preview asset not found")
    return target


def inject_preview_bridge(markup: str, *, session_id: str) -> str:
    base = f'<base href="/api/design/preview/{session_id}/asset/">'
    script = f"""
<script>
(() => {{
  const sessionId = {session_id!r};
  function selectorFor(node) {{
    if (!node || node.nodeType !== 1) return "";
    if (node.id) return "#" + CSS.escape(node.id);
    const parts = [];
    let current = node;
    while (current && current.nodeType === 1 && current !== document.body) {{
      let part = current.tagName.toLowerCase();
      if (current.classList.length) part += "." + Array.from(current.classList).slice(0, 3).map((item) => CSS.escape(item)).join(".");
      const parent = current.parentElement;
      if (parent) {{
        const siblings = Array.from(parent.children).filter((child) => child.tagName === current.tagName);
        if (siblings.length > 1) part += ":nth-of-type(" + (siblings.indexOf(current) + 1) + ")";
      }}
      parts.unshift(part);
      current = parent;
    }}
    return parts.join(" > ");
  }}
  function clear() {{
    document.querySelectorAll("[data-keprix-preview-selected]").forEach((node) => {{
      node.removeAttribute("data-keprix-preview-selected");
      node.style.outline = node.dataset.keprixPreviousOutline || "";
      delete node.dataset.keprixPreviousOutline;
    }});
  }}
  document.addEventListener("keydown", (event) => {{
    if (event.key === "Escape") clear();
  }});
  document.addEventListener("click", (event) => {{
    const target = event.target;
    if (!(target instanceof Element)) return;
    event.preventDefault();
    event.stopPropagation();
    clear();
    target.dataset.keprixPreviewSelected = "true";
    target.dataset.keprixPreviousOutline = target.style.outline || "";
    target.style.outline = "2px solid #2563eb";
    const rect = target.getBoundingClientRect();
    const payload = {{
      selector: selectorFor(target),
      html_snippet: target.outerHTML.slice(0, 4000),
      meta: {{
        tag: target.tagName.toLowerCase(),
        id: target.id || "",
        classes: Array.from(target.classList),
        bbox: {{ x: rect.x, y: rect.y, width: rect.width, height: rect.height }},
      }},
    }};
    window.parent.postMessage({{ type: "keprix-design-selection", session_id: sessionId, ...payload }}, window.location.origin);
    fetch("/api/design/preview/" + encodeURIComponent(sessionId) + "/selection", {{
      method: "POST",
      headers: {{ "Content-Type": "application/json" }},
      body: JSON.stringify(payload),
    }}).catch(() => undefined);
  }}, true);
}})();
</script>
"""
    lower = markup.lower()
    if "<head" in lower and "</head>" in lower and "<base " not in lower:
        head_end = lower.find(">", lower.find("<head")) + 1
        markup = markup[:head_end] + base + markup[head_end:]
        lower = markup.lower()
    if "</body>" in lower:
        index = lower.rfind("</body>")
        return markup[:index] + script + markup[index:]
    return markup + script


def render_session_html(session: PreviewSession) -> str:
    entry = resolve_session_file(session)
    markup = entry.read_text(encoding="utf-8", errors="replace")
    return inject_preview_bridge(markup, session_id=session.session_id)


def build_design_skill_message(session: PreviewSession) -> str:
    selector = session.selected_selector or "(no selector selected)"
    snippet = session.selected_html_snippet or ""
    root = session.root_path or session.artifact_id or ""
    return (
        "/skill claude-design\n"
        "/skill impeccable\n\n"
        "Improve the selected UI component while preserving product behavior.\n\n"
        f"Preview session: {session.session_id}\n"
        f"File context: {root}/{session.entry_file}\n"
        f"Selector: {selector}\n"
        f"Selection metadata: {session.selected_meta}\n\n"
        "HTML snippet:\n"
        f"```html\n{html.unescape(snippet)[:4000]}\n```"
    )


def session_mtime(session: PreviewSession) -> float:
    try:
        return resolve_session_file(session).stat().st_mtime
    except HTTPException:
        return 0.0
