"""VPS hardening assets for Prompt 270 follow-up."""

from __future__ import annotations

from pathlib import Path


def test_deploy_hardening_assets_exist() -> None:
    root = Path(__file__).resolve().parents[2]
    required = [
        "deploy/keprix.service",
        "deploy/Caddyfile",
        "deploy/nginx.conf",
        "deploy/keprix-backup.service",
        "deploy/keprix-backup.timer",
        "deploy/logrotate-keprix",
        "deploy/journald-keprix.conf",
        "deploy/keprix.env.example",
        "docker/docker-compose.prod.yml",
        "scripts/deploy-server.sh",
        "scripts/configure-firewall.sh",
        "scripts/generate-production-env.sh",
        "docs/operations/vps-deploy.md",
    ]
    for rel in required:
        assert (root / rel).is_file(), rel


def test_systemd_unit_binds_localhost() -> None:
    root = Path(__file__).resolve().parents[2]
    unit = (root / "deploy" / "keprix.service").read_text(encoding="utf-8")
    assert "127.0.0.1" in unit
    assert "0.0.0.0" not in unit
    assert "User=@KEPRIX_USER@" in unit
    assert "NoNewPrivileges=true" in unit
    assert "EnvironmentFile=-/etc/keprix.env" in unit
    assert "uvicorn keprix.api.main:app" in unit


def test_compose_prod_removes_db_host_ports() -> None:
    root = Path(__file__).resolve().parents[2]
    prod = (root / "docker" / "docker-compose.prod.yml").read_text(encoding="utf-8")
    assert "ports: !override []" in prod
    base = (root / "docker" / "docker-compose.yml").read_text(encoding="utf-8")
    assert "/home/keprix/.keprix" in base
    assert "POSTGRES_PASSWORD:?set POSTGRES_PASSWORD" in base


def test_deploy_server_is_fail_closed() -> None:
    root = Path(__file__).resolve().parents[2]
    script = (root / "scripts" / "deploy-server.sh").read_text(encoding="utf-8")
    assert "die " in script
    assert "alembic upgrade head" in script
    assert "api/health" in script
    # Critical gates must not be soft-failed
    assert "cli doctor || true" not in script
    assert "backup --quick || true" not in script
    assert 'curl -fsS "http://127.0.0.1:${PORT}/api/health" && echo || echo' not in script
    assert "die \"doctor failed\"" in script or "die \"doctor failed\"" in script.replace("'", '"')
    assert "die \"backend health failed" in script
