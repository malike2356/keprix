"""GTM path smoke tests: billing trial mode, upgrade channel, activation onboarding."""

from __future__ import annotations

from pathlib import Path

from keprix.agent_os.onboarding_progress import OnboardingProgress
from keprix.agent_os.onboarding_steps import activation_step_ids, STEPS
from keprix.upgrade.service import UpgradeService


def test_activation_steps_are_first_track():
    activation = [s for s in STEPS if s.track == "activation"]
    assert [s.id for s in activation] == ["a1_provider", "a2_first_chat", "a3_channel"]
    assert set(activation_step_ids()) == {"a1_provider", "a2_first_chat", "a3_channel"}


def test_banner_hides_when_activation_complete():
    progress = OnboardingProgress(user_id="gtm-user", steps={})
    progress.normalize()
    for step_id in activation_step_ids():
        progress.steps[step_id] = True
    payload = progress.to_dict()
    assert payload["activation_completed"] is True
    assert payload["banner_visible"] is False
    assert payload["next_activation"] is None


def test_banner_points_at_next_activation_action():
    progress = OnboardingProgress(user_id="gtm-user", steps={})
    progress.normalize()
    payload = progress.to_dict()
    assert payload["banner_visible"] is True
    assert payload["next_activation"]["id"] == "a1_provider"
    assert payload["next_activation"]["action_url"] == "/auth/setup"


def test_upgrade_status_exposes_channel(tmp_path: Path, monkeypatch):
    (tmp_path / "keprix.yaml").write_text(
        """
product:
  name: GtmProduct
  slug: gtmproduct
keprix:
  min_version: "0.2.0"
  tested_against: "0.16.0"
features: {}
""".strip()
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("keprix.upgrade.context.installed_keprix_version", lambda: "0.16.0")
    monkeypatch.setattr(
        "keprix.upgrade.installability.check_target_installable",
        lambda version, runner=None, cwd=None: type(
            "R", (), {"available": False, "recommendation": f"{version} not on index", "command": [], "detail": ""}
        )(),
    )
    status = UpgradeService(tmp_path).status()
    assert "channel" in status
    assert status["current_version"] == "0.16.0"
    assert status["channel"] in {"current", "stable", "changelog_only"}
