"""Prompt 260 skill-to-automation promoter tests."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from keprix.agent_apps.app_manifest import load_manifest
from keprix.agent_os.automation_link_store import AutomationLinkStore
from keprix.agent_os.automation_promoter import AutomationPromoter
from keprix.agent_os.cli_commands import _dispatch_links, _dispatch_promote
from keprix.api.server import create_app
from keprix.auth.dependencies import get_current_user
from keprix.playbook.yaml_compiler import compile_playbook_document


@pytest.fixture
def promoter_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / ".keprix"
    root.mkdir()
    monkeypatch.setenv("KEPRIX_HOME", str(root))
    monkeypatch.setenv("KEPRIX_AGENT_OS_ENABLED", "1")
    skill_dir = root / "skills" / "daily-brief"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: daily-brief\ndescription: Build a daily brief\n---\n\n# Daily brief\n",
        encoding="utf-8",
    )
    return root


def test_link_store_roundtrip_and_remove(promoter_home: Path) -> None:
    store = AutomationLinkStore()
    link = store.add(skill_slug="daily-brief", automation_type="cron", automation_id="job1", edit_url="/admin/cron")

    assert store.list("daily-brief")[0].link_id == link.link_id
    assert store.remove("cron", "job1") == 1
    assert store.list("daily-brief") == []


def test_promote_skill_to_cron_creates_job_and_link(promoter_home: Path) -> None:
    from keprix.cron.jobs import list_jobs

    result = AutomationPromoter().promote(
        skill_slug="daily-brief",
        target="cron",
        schedule="every 1h",
        name="daily brief",
        deliver_to="local",
    )

    jobs = list_jobs(include_disabled=True)
    assert any(job["id"] == result["id"] for job in jobs)
    assert result["link"]["automation_type"] == "cron"
    assert result["artifact"]["skills"] == ["daily-brief"]


def test_promote_skill_to_playbook_creates_valid_yaml(promoter_home: Path) -> None:
    result = AutomationPromoter().promote(skill_slug="daily-brief", target="playbook", name="daily brief")
    path = Path(result["link"]["metadata"]["path"])
    document = yaml.safe_load(path.read_text(encoding="utf-8"))

    assert compile_playbook_document(document).graph_id == result["id"]
    assert result["link"]["automation_type"] == "playbook"


def test_promote_skill_to_agent_app_creates_installable_manifest(promoter_home: Path) -> None:
    result = AutomationPromoter().promote(skill_slug="daily-brief", target="agent_app", schedule="0 8 * * 1-5")
    app_dir = Path(result["link"]["metadata"]["path"])
    manifest = load_manifest(app_dir)

    assert manifest.name == "daily-brief"
    assert manifest.runtime == "agent"
    assert manifest.schedule is not None


def test_promote_routes_and_links(promoter_home: Path) -> None:
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: {"id": "u1", "role": "user"}
    client = TestClient(app)

    promoted = client.post("/api/agent-os/promote", json={"skill_slug": "daily-brief", "target": "playbook", "name": "daily brief"})
    assert promoted.status_code == 200
    links = client.get("/api/agent-os/links?skill=daily-brief")
    assert links.status_code == 200
    assert links.json()["links"][0]["automation_type"] == "playbook"
    removed = client.delete(f"/api/agent-os/links/playbook/{promoted.json()['id']}")
    assert removed.json()["removed"] == 1


def test_agent_os_promote_cli(promoter_home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    import argparse

    args = argparse.Namespace(skill="daily-brief", to="agent-app", schedule=None, name=None, deliver_to=None)
    assert _dispatch_promote(args) == 0
    assert "agent_app" in capsys.readouterr().out

    link_args = argparse.Namespace(skill="daily-brief")
    assert _dispatch_links(link_args) == 0
    assert "daily-brief" in capsys.readouterr().out
