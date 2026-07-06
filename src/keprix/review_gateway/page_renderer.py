"""HTML pages for external reviewers."""

from __future__ import annotations

import html
import re
from typing import Any

from keprix.review_gateway.store import ReviewRequest


def _markdown_to_html(source: str) -> str:
    text = html.escape(source)
    text = re.sub(r"^### (.+)$", r"<h3>\1</h3>", text, flags=re.MULTILINE)
    text = re.sub(r"^## (.+)$", r"<h2>\1</h2>", text, flags=re.MULTILINE)
    text = re.sub(r"^# (.+)$", r"<h1>\1</h1>", text, flags=re.MULTILINE)
    text = text.replace("\n\n", "</p><p>")
    return f"<p>{text}</p>"


def _artifact_html(req: ReviewRequest) -> str:
    if req.artifact_type == "markdown":
        return f'<div class="artifact">{_markdown_to_html(req.artifact_content)}</div>'
    if req.artifact_type == "pdf" and req.artifact_url:
        safe_url = html.escape(req.artifact_url)
        filename = html.escape(req.artifact_filename or "document.pdf")
        return (
            f'<iframe class="artifact-pdf" src="{safe_url}" title="{filename}"></iframe>'
            f'<p><a href="{safe_url}" download>Download {filename}</a></p>'
        )
    if req.artifact_type == "url" and req.artifact_url:
        safe_url = html.escape(req.artifact_url)
        return (
            f'<p class="warning">This links to external content.</p>'
            f'<p><a href="{safe_url}" rel="noopener noreferrer">{safe_url}</a></p>'
        )
    if req.artifact_type == "json":
        return f'<pre class="artifact">{html.escape(req.artifact_content)}</pre>'
    return "<p>No artifact attached.</p>"


def render_review_page(
    req: ReviewRequest,
    *,
    workspace_name: str,
    url_token: str,
    csrf_token: str,
) -> str:
    actions = "".join(
        f'<button type="submit" name="action" value="{html.escape(action)}">{html.escape(action.replace("_", " ").title())}</button>'
        for action in req.allowed_actions
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(req.title)}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem auto; max-width: 720px; line-height: 1.5; }}
    .card {{ border: 1px solid #ddd; border-radius: 8px; padding: 1.5rem; }}
    .artifact-pdf {{ width: 100%; min-height: 480px; border: 1px solid #ccc; }}
    .warning {{ color: #8a4b00; }}
    textarea {{ width: 100%; min-height: 100px; }}
    button {{ margin-right: 0.5rem; margin-top: 0.5rem; padding: 0.5rem 1rem; }}
  </style>
</head>
<body>
  <div class="card">
    <p><strong>{html.escape(workspace_name)}</strong></p>
    <h1>{html.escape(req.title)}</h1>
    <p>{html.escape(req.context_message)}</p>
    {_artifact_html(req)}
    <form method="post" action="/review/{html.escape(url_token)}">
      <input type="hidden" name="csrf_token" value="{html.escape(csrf_token)}">
      <p><label>Reviewer: <input type="text" name="reviewer_name" value="{html.escape(req.reviewer_name)}" readonly></label></p>
      <p><label>Note (optional)<br><textarea name="reviewer_note" maxlength="2000"></textarea></label></p>
      <div>{actions}</div>
    </form>
  </div>
</body>
</html>"""


def render_invalid_page() -> str:
    return """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Review link invalid</title></head>
<body><p>This review link is no longer valid.</p></body></html>"""


def render_confirmation_page(action: str) -> str:
    label = html.escape(action.replace("_", " "))
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Decision recorded</title></head>
<body><p>Your decision ({label}) has been recorded. You can close this page.</p></body></html>"""


def render_gone_page() -> str:
    return """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Review complete</title></head>
<body><p>This review link has already been used.</p></body></html>"""
