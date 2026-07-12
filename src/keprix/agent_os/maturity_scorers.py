"""Four C's maturity scoring heuristics."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from keprix.agent_os.maturity_audit_store import MaturityScore
from keprix_constants import get_keprix_home

TIER1_DOMAINS = ("revenue", "customer", "calendar", "comms", "tasks", "meetings", "knowledge")


def _text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def score_context(root: Path) -> MaturityScore:
    context = root / "context"
    score = 0.0
    strengths: list[str] = []
    gaps: list[str] = []
    about_business = _text(context / "about-business.md").lower()
    if about_business and any(term in about_business for term in ("offer", "sell", "icp", "customer")):
        score += 8
        strengths.append("Business/ICP context exists")
    else:
        gaps.append("Add context/about-business.md with offer and ICP")
    if _text(context / "about-me.md").strip():
        score += 5
        strengths.append("Operator context exists")
    else:
        gaps.append("Add context/about-me.md")
    priorities = _text(context / "priorities.md").lower()
    if priorities and ("90" in priorities or "priority" in priorities or "-" in priorities):
        score += 7
        strengths.append("90-day priorities are present")
    else:
        gaps.append("Add 2-3 priorities in context/priorities.md")
    if _text(context / "writing-samples.md").strip() or (context / "intake.json").is_file():
        score += 5
        strengths.append("Writing samples or onboard intake present")
    else:
        gaps.append("Add verbatim writing samples or complete onboard interview")
    return MaturityScore("context", min(score, 25), strengths, gaps)


def score_connections(root: Path) -> tuple[MaturityScore, list[str]]:
    text = _text(root / "connections.md").lower()
    score = 0.0
    strengths: list[str] = []
    gaps: list[str] = []
    missing: list[str] = []
    for domain in TIER1_DOMAINS:
        if domain in text and "status: live" in text[text.find(domain) : text.find(domain) + 160]:
            score += 3.5
            strengths.append(f"{domain} connection live")
        elif domain in text and ("status: draft" in text[text.find(domain) : text.find(domain) + 160] or "status: partial" in text[text.find(domain) : text.find(domain) + 160]):
            score += 1.5
            missing.append(domain)
            gaps.append(f"Finish {domain} connection")
        else:
            missing.append(domain)
    if not strengths:
        gaps.append("Create connections.md with tier-1 domains and status fields")
    return MaturityScore("connections", min(score, 25), strengths, gaps), missing


def score_capabilities(root: Path | None = None) -> MaturityScore:
    home = get_keprix_home()
    skill_count = 0
    for base in (home / "skills", home / "hub" / "installed", Path.cwd() / "src" / "keprix" / "optional-skills"):
        if base.exists():
            skill_count += sum(1 for path in base.rglob("SKILL.md"))
    automation_links = home / "agent-os" / "automation-links.json"
    promoted = home / "playbooks" / "promoted"
    headless = home / "agent-os" / "headless-runs"
    score = 0.0
    strengths: list[str] = []
    gaps: list[str] = []
    if skill_count >= 3:
        score += 8
        strengths.append(f"{skill_count} skills available")
    else:
        gaps.append("Install or approve at least three skills")
    if automation_links.is_file() or (promoted.exists() and any(promoted.iterdir())):
        score += 9
        strengths.append("Promoted automation exists")
    else:
        gaps.append("Promote one skill to an automation")
    if headless.exists() and any(headless.iterdir()):
        score += 8
        strengths.append("Headless action run exists")
    else:
        gaps.append("Run one action headlessly")
    return MaturityScore("capabilities", min(score, 25), strengths, gaps)


def score_cadence(root: Path) -> MaturityScore:
    home = get_keprix_home()
    cron_jobs = home / "cron" / "jobs.json"
    ledger_entries = home / "agent-os" / "run-ledger" / "entries"
    score = 0.0
    strengths: list[str] = []
    gaps: list[str] = []
    cron_text = _text(cron_jobs).lower()
    if cron_text and "disabled" not in cron_text:
        score += 10
        strengths.append("Active cron cadence exists")
    else:
        gaps.append("Create one active cron cadence")
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    recent_run = False
    if ledger_entries.exists():
        for path in ledger_entries.glob("*.json"):
            try:
                if datetime.fromtimestamp(path.stat().st_mtime, timezone.utc) >= cutoff:
                    recent_run = True
                    break
            except OSError:
                pass
    if recent_run:
        score += 8
        strengths.append("Recent run ledger entry exists")
    else:
        gaps.append("Run one automation and record it in the ledger")
    weekly_doc = (_text(root / "context" / "cadence-preferences.md") + "\n" + cron_text).lower()
    if "weekly" in weekly_doc and "audit" in weekly_doc:
        score += 7
        strengths.append("Weekly audit cadence documented")
    else:
        gaps.append("Document or schedule a weekly audit cadence")
    return MaturityScore("cadence", min(score, 25), strengths, gaps)
