"""Day-1 Hello World workflow for Agent OS (Prompt 270 Task 1.5).

One command → working result in under five minutes. Reuses the portable
hello-agent sample app and writes the run into the single vault.
"""

from __future__ import annotations

import importlib.util
from typing import Any
from uuid import uuid4

from keprix.agent_apps.registry import sample_app_dir
from keprix.vault.capture import capture_conversation, ensure_default_vault


def _load_hello_runner():
    entry = sample_app_dir() / "agents" / "main.py"
    spec = importlib.util.spec_from_file_location("keprix_hello_agent_main", entry)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"hello-agent entrypoint missing: {entry}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    run = getattr(module, "run", None)
    if not callable(run):
        raise RuntimeError("hello-agent run() not found")
    return run


async def run_hello_world(*, name: str = "world", capture: bool = True) -> dict[str, Any]:
    """Run the Hello World workflow and optionally capture it to the vault."""
    ensure_default_vault()
    runner = _load_hello_runner()
    result = runner("", {"form": {"name": name}})
    output = str(result.get("output") or "")
    session_id = f"hello-{uuid4().hex[:12]}"
    messages = [
        {"role": "user", "content": f"Hello World workflow for {name}"},
        {"role": "assistant", "content": output},
    ]
    capture_result: dict[str, Any] | None = None
    if capture:
        capture_result = await capture_conversation(
            session_id=session_id,
            messages=messages,
            title=f"Hello World: {name}",
            source="hello-world",
            agent_id="hello-agent",
        )
    try:
        from keprix.agent_os.onboarding_events import record_onboarding_event

        record_onboarding_event("cli", "hello_world.completed")
        record_onboarding_event("cli", "vault.configured")
    except Exception:
        pass
    return {
        "ok": True,
        "workflow": "hello-world",
        "session_id": session_id,
        "result": result,
        "output": output,
        "sample_app": str(sample_app_dir()),
        "capture": capture_result,
        "next_steps": [
            "Open /agent-apps and install Hello Agent for the UI path",
            "Connect a provider with: keprix model",
            "Chat at /chat or run: keprix chat",
            "Vault notes land under conversations/ in your single vault",
        ],
    }


def hello_world_readme() -> str:
    return (
        "Keprix Hello World\n"
        "==================\n"
        "\n"
        "1. keprix agent-os hello --name You\n"
        "2. Confirm the greeting prints and a vault note was written\n"
        "3. keprix model   # switch Grok / GPT / Claude with one command\n"
        "4. Open /chat for your first live conversation (auto-captured)\n"
    )
