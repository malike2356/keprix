"""Tests for keprix.seams (capability seams, prompt 768)."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from keprix.seams import (
    SEAM_IDS,
    SeamPolicyDenied,
    ensure_default_seams,
    get_fs,
    get_llm,
    get_memory,
    get_seam_registry,
    get_shell,
    get_subagent,
    get_web,
    reset_seams_for_tests,
)
from keprix.seams.providers import LocalFsProvider, SandboxedFsProvider
from keprix.seams.policy import PolicyWrappedFs


ROOT = Path(__file__).resolve().parents[4]  # keprix repo root


@pytest.fixture(autouse=True)
def _fresh_seams(tmp_path):
    reset_seams_for_tests(sandbox_root=tmp_path / "sandbox", memory_base=tmp_path / "mem")
    yield
    reset_seams_for_tests(sandbox_root=tmp_path / "sandbox2", memory_base=tmp_path / "mem2")


def test_all_six_seams_have_active_providers():
    reg = get_seam_registry()
    snap = reg.snapshot()
    for seam in SEAM_IDS:
        assert snap[seam]["active"], f"missing active provider for {seam}"
        assert snap[seam]["providers"], f"no providers registered for {seam}"


def test_registry_resolves_definition_to_provider():
    fs = get_fs()
    assert hasattr(fs, "read_text")
    assert hasattr(fs, "write_text")
    assert get_shell().provider_id
    assert get_memory().provider_id == "memory.default"
    assert get_llm().provider_id == "llm.default"
    assert get_subagent().provider_id == "subagent.default"
    assert get_web().provider_id.startswith("policy:")


def test_consumer_uses_definition_only_with_mock_provider(tmp_path):
    """Consumer path depends on Definition methods, not a concrete class name."""

    class MockFs:
        provider_id = "fs.mock"

        def read_text(self, path: str, *, encoding: str = "utf-8") -> str:
            return f"mock:{path}"

        def write_text(self, path: str, content: str, *, encoding: str = "utf-8") -> None:
            (tmp_path / path).write_text(content, encoding=encoding)

        def exists(self, path: str) -> bool:
            return (tmp_path / path).exists()

        def list_dir(self, path: str = ".") -> list[str]:
            return sorted(p.name for p in tmp_path.iterdir())

        def tool_schemas(self):
            return [{"name": "read_file", "seam": "fs"}]

    reg = get_seam_registry()
    reg.register("fs", MockFs(), make_active=True)

    def consumer_read(name: str) -> str:
        # Definition-only: no isinstance checks against LocalFsProvider.
        return get_fs().read_text(name)

    assert consumer_read("x") == "mock:x"
    get_fs().write_text("a.txt", "hi")
    assert get_fs().exists("a.txt")


def test_provider_swap_fs_changes_behaviour_without_editing_consumer(tmp_path):
    sandbox = tmp_path / "box"
    sandbox.mkdir()
    local_root = tmp_path / "local"
    local_root.mkdir()

    reg = get_seam_registry()
    reg.register("fs", LocalFsProvider(local_root), make_active=True)
    reg.register("fs", SandboxedFsProvider(sandbox))

    def consumer_write_and_list(filename: str, content: str) -> list[str]:
        fs = get_fs()
        fs.write_text(filename, content)
        return fs.list_dir(".")

    assert consumer_write_and_list("from-local.txt", "L") == ["from-local.txt"]
    assert (local_root / "from-local.txt").read_text() == "L"
    assert not (sandbox / "from-local.txt").exists()

    reg.set_active("fs", "fs.sandboxed")
    assert consumer_write_and_list("from-sandbox.txt", "S") == ["from-sandbox.txt"]
    assert (sandbox / "from-sandbox.txt").read_text() == "S"
    assert not (local_root / "from-sandbox.txt").exists()

    # Related tool schema metadata stays stable across swap.
    names_local = {s["name"] for s in LocalFsProvider(local_root).tool_schemas()}
    names_box = {s["name"] for s in SandboxedFsProvider(sandbox).tool_schemas()}
    assert names_local == names_box
    assert "read_file" in names_local


def test_soft_wall_hardline_gates_shell_provider():
    shell = get_shell()
    result = shell.execute("rm -rf /")
    assert result.get("blocked") is True or result.get("returncode") == 126
    assert result.get("error_code") == "hardline_blocked"


def test_vault_floor_gates_fs_write(tmp_path):
    fs = PolicyWrappedFs(LocalFsProvider(tmp_path))
    with pytest.raises(SeamPolicyDenied) as exc:
        fs.write_text(".access/secret.env", "x=1")
    assert exc.value.error_code == "vault_floor_denied"


def test_memory_is_workspace_scoped(tmp_path):
    mem = get_memory()
    mem.append_entry("MEMORY", "alpha", workspace_id="t1")
    mem.append_entry("MEMORY", "beta", workspace_id="t2")
    assert "alpha" in mem.read_store("MEMORY", workspace_id="t1")
    assert "alpha" not in mem.read_store("MEMORY", workspace_id="t2")
    assert "beta" in mem.read_store("MEMORY", workspace_id="t2")


def test_no_cordis_or_dsh_runtime_dependency():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    deps = [str(d).lower() for d in pyproject.get("project", {}).get("dependencies", [])]
    forbidden = ("cordis", "deepseek-harness", "deepseek_harness", "@deepseek-ai/dsh")
    for dep in deps:
        for bad in forbidden:
            assert bad not in dep, f"forbidden runtime dependency: {dep}"

    # Also scan lock-ish / requirements if present.
    for name in ("requirements.txt", "uv.lock", "poetry.lock"):
        path = ROOT / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace").lower()
        for bad in ("cordis", "deepseek-harness"):
            assert bad not in text, f"{name} mentions forbidden package {bad}"


def test_ensure_default_seams_idempotent():
    a = ensure_default_seams()
    b = ensure_default_seams()
    assert a is b
    assert get_seam_registry().active_id("fs")
