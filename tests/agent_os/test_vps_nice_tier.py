"""Nice-tier VPS: canary, signed install, fly fullstack, droplet bootstrap assets."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_nice_tier_assets_exist() -> None:
    required = [
        "scripts/bootstrap-do-droplet.sh",
        "scripts/deploy-canary.sh",
        "scripts/deploy-keprix-production.sh",
        "scripts/build-release-artifact.sh",
        "scripts/sign-release.sh",
        "scripts/verify-release.sh",
        "scripts/install-verified.sh",
        "scripts/install-curl.sh",
        "docker/docker-compose.canary.yml",
        "docker/Dockerfile.fly",
        "docker/start-fly.sh",
        "fly.fullstack.toml",
        "fly.backend-only.toml",
        "fly.toml",
        "deploy/Caddyfile.template",
        "deploy/keys/README.md",
        "docs/security/release-signing.md",
    ]
    for rel in required:
        assert (ROOT / rel).is_file(), rel


def test_install_curl_blocks_unsafe_pipe() -> None:
    text = (ROOT / "scripts" / "install-curl.sh").read_text(encoding="utf-8")
    assert "KEPRIX_ALLOW_UNSAFE_CURL_BASH" in text
    assert "exit 1" in text
    assert "install-verified.sh" in text


def test_fly_fullstack_not_scale_to_zero() -> None:
    text = (ROOT / "fly.fullstack.toml").read_text(encoding="utf-8")
    assert 'min_machines_running = 1' in text
    assert 'auto_stop_machines = "off"' in text
    assert "keprix_data" in text
    assert "Dockerfile.fly" in text
    assert "one-click" not in text.lower() or "not" in text.lower()


def test_droplet_bootstrap_requires_ssh_key() -> None:
    text = (ROOT / "scripts" / "bootstrap-do-droplet.sh").read_text(encoding="utf-8")
    assert "--ssh-key" in text
    assert "install.sh | bash" not in text
    assert "configure-firewall.sh" in text
    assert "caddy" in text.lower()


def test_canary_script_flips_proxy() -> None:
    text = (ROOT / "scripts" / "deploy-canary.sh").read_text(encoding="utf-8")
    assert "Caddyfile.template" in text
    assert "CANARY_FRONTEND" in text
    assert "render_caddy" in text
    assert "api/health" in text


def test_production_script_is_canonical() -> None:
    text = (ROOT / "scripts" / "deploy-keprix-production.sh").read_text(encoding="utf-8")
    assert "Canonical production deploy" in text or "Compose + Caddy" in text
    assert "deploy-canary.sh" in text
    assert "placeholder secrets" in text
    assert "Optional helpers" in text or "optional helpers" in text.lower()
