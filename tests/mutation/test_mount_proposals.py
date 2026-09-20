"""Tests for mutation-as-mount (prompt 773)."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from keprix.mutation.mount import (
    MountApprovalError,
    MountBanError,
    MountIntent,
    assert_mount_allowed,
    map_legacy_mutation_to_intent,
    reset_mutation_mount_service_for_tests,
)
from keprix.plugin_lifecycle import get_lifecycle_ledger, reset_lifecycle_for_tests
from keprix.seams import ensure_default_seams, get_seam_registry, reset_seams_for_tests
from keprix.trajectory.service import reset_trajectory_service_for_tests
from tools.registry import registry as tool_registry


ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def _fresh(tmp_path):
    reset_lifecycle_for_tests()
    reset_seams_for_tests(sandbox_root=tmp_path / "sb", memory_base=tmp_path / "mem")
    svc = reset_mutation_mount_service_for_tests(sqlite_path=tmp_path / "mount.db")
    for name in list(getattr(tool_registry, "_tools", {})):
        if name.startswith("mutation_mount_test_") or name.startswith("skill_marker_"):
            tool_registry.deregister(name)
    yield svc
    reset_lifecycle_for_tests()
    for name in list(getattr(tool_registry, "_tools", {})):
        if name.startswith("mutation_mount_test_") or name.startswith("skill_marker_"):
            tool_registry.deregister(name)


def test_map_legacy_kinds():
    assert map_legacy_mutation_to_intent(kind="enable_plugin", name="demo").action == (
        "mount_plugin"
    )
    assert map_legacy_mutation_to_intent(kind="disable_skill", name="x").action == (
        "unmount_skill"
    )
    swap = map_legacy_mutation_to_intent(
        kind="swap_provider",
        name="fs",
        detail={"seam": "fs", "provider_id": "policy:fs.sandboxed"},
    )
    assert swap.action == "swap_provider"
    assert swap.provider_id == "policy:fs.sandboxed"


def test_banned_soft_wall_and_rls():
    with pytest.raises(MountBanError):
        assert_mount_allowed(action="unmount_plugin", target_id="soft-wall")
    with pytest.raises(MountBanError):
        assert_mount_allowed(
            action="mount_plugin",
            target_id="helper",
            metadata={"disable_soft_wall": True},
        )
    with pytest.raises(MountBanError):
        assert_mount_allowed(
            action="mount_plugin",
            target_id="helper",
            metadata={"drop_rls": True},
        )
    with pytest.raises(MountBanError):
        assert_mount_allowed(action="mount_plugin", target_id="billing-helper")
    with pytest.raises(MountBanError):
        assert_mount_allowed(
            action="swap_provider",
            target_id="shell",
            seam="shell",
            provider_id="shell.unrestricted",
        )


def test_deny_leaves_registry_unchanged(_fresh):
    svc = _fresh
    before = get_lifecycle_ledger().snapshot()
    proposal = svc.propose(
        MountIntent(
            action="mount_plugin",
            target_id="mutation-demo-plugin",
            declared_tools=[
                {"name": "mutation_mount_test_alpha", "description": "t"},
            ],
        ),
        proposed_by="agent",
    )
    denied = svc.deny(proposal.id, denied_by="operator", reason="nope")
    assert denied.status == "denied"
    assert get_lifecycle_ledger().snapshot() == before
    assert tool_registry.get_entry("mutation_mount_test_alpha") is None


def test_approve_mounts_via_lifecycle_four_eyes(_fresh):
    svc = _fresh
    proposal = svc.propose(
        MountIntent(
            action="mount_plugin",
            target_id="mutation-demo-plugin",
            declared_tools=[
                {"name": "mutation_mount_test_beta", "description": "t"},
            ],
        ),
        proposed_by="agent",
    )
    with pytest.raises(MountApprovalError):
        svc.approve(proposal.id, approved_by="agent")
    mounted = svc.approve(proposal.id, approved_by="operator")
    assert mounted.status == "mounted"
    assert tool_registry.get_entry("mutation_mount_test_beta") is not None
    ledger = get_lifecycle_ledger().get("mutation-demo-plugin")
    assert ledger is not None
    assert "mutation_mount_test_beta" in ledger.tools

    reversed_p = svc.reverse(mounted.id, who="operator")
    assert reversed_p.status == "reversed"
    assert tool_registry.get_entry("mutation_mount_test_beta") is None


def test_approve_unmount_after_mount(_fresh):
    svc = _fresh
    mount = svc.propose(
        MountIntent(
            action="mount_plugin",
            target_id="mutation-demo-plugin",
            declared_tools=[{"name": "mutation_mount_test_gamma"}],
        ),
        proposed_by="agent",
    )
    svc.approve(mount.id, approved_by="operator")
    assert tool_registry.get_entry("mutation_mount_test_gamma") is not None

    remove = svc.propose(
        MountIntent(action="unmount_plugin", target_id="mutation-demo-plugin"),
        proposed_by="agent",
    )
    svc.approve(remove.id, approved_by="operator")
    assert tool_registry.get_entry("mutation_mount_test_gamma") is None
    assert get_lifecycle_ledger().get("mutation-demo-plugin") is None


def test_trajectory_propose_approve_mount(tmp_path, _fresh):
    svc = _fresh
    traj_svc = reset_trajectory_service_for_tests(sqlite_path=tmp_path / "traj.db")
    traj = traj_svc.create(workspace_id="default", title="mount-flow")
    tid = traj["trajectory_id"]
    proposal = svc.propose(
        MountIntent(
            action="mount_plugin",
            target_id="mutation-demo-plugin",
            declared_tools=[{"name": "mutation_mount_test_delta"}],
        ),
        proposed_by="agent",
        trajectory_id=tid,
    )
    svc.approve(proposal.id, approved_by="operator")
    events = traj_svc.store.list_events(tid)
    stages = [e.payload.get("stage") for e in events if e.event_type == "mutation"]
    assert stages == ["propose", "approve", "mount"]


def test_swap_provider_recorded(_fresh):
    svc = _fresh
    ensure_default_seams()
    reg = get_seam_registry()
    # Prefer sandboxed if present
    providers = reg.list_providers("fs")
    assert providers
    target = "policy:fs.sandboxed" if "policy:fs.sandboxed" in providers else providers[-1]
    proposal = svc.propose(
        MountIntent(
            action="swap_provider",
            target_id="fs",
            seam="fs",
            provider_id=target,
        ),
        proposed_by="agent",
    )
    applied = svc.approve(proposal.id, approved_by="operator")
    assert applied.status == "mounted"
    assert reg.active_id("fs") == target


def test_no_cordis_dependency():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    deps = [str(d).lower() for d in pyproject.get("project", {}).get("dependencies", [])]
    for dep in deps:
        assert "cordis" not in dep
        assert "deepseek-harness" not in dep
