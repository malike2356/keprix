"""Issue and repository parsers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse


_GITHUB_ISSUE = re.compile(r"github\.com/([^/]+)/([^/]+)/issues/(\d+)")


@dataclass
class ParsedIssue:
    source: str
    title: str
    body: str
    repo_hint: str | None = None
    issue_number: str | None = None


def parse_issue_input(issue: str) -> ParsedIssue:
    text = issue.strip()
    if text.startswith("http"):
        parsed = urlparse(text)
        match = _GITHUB_ISSUE.search(parsed.geturl())
        if match:
            owner, repo, number = match.groups()
            return ParsedIssue(
                source=text,
                title=f"{owner}/{repo}#{number}",
                body=text,
                repo_hint=f"{owner}/{repo}",
                issue_number=number,
            )
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    title = lines[0] if lines else text
    body = "\n".join(lines[1:]) if len(lines) > 1 else text
    return ParsedIssue(source=text, title=title, body=body)


def extract_target_file(issue: ParsedIssue) -> str | None:
    match = re.search(r"\b([A-Za-z0-9_./-]+\.(?:py|ts|tsx|js|md|yaml|yml|json|toml))\b", issue.body)
    return match.group(1) if match else None


def extract_replacement_text(issue: ParsedIssue) -> str | None:
    match = re.search(r"replace\s+['\"](.+?)['\"]\s+with\s+['\"](.+?)['\"]", issue.body, re.I)
    if match:
        return match.group(2)
    if "add comment" in issue.body.lower() or "add marker" in issue.body.lower():
        return "# Keprix coding marker\n"
    return None
