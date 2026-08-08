"""Register Fleetz tools on the pack registry."""

from __future__ import annotations

from tools import handlers
from tools.contract import ALL_LIVE_NODES, DISABLED_COMMAND_NODES
from tools.registry import registry

for bare in ALL_LIVE_NODES:
    name = f"fleetz_{bare}"
    handler = getattr(handlers, f"{name}_handler", None)
    if handler is None:
        raise RuntimeError(f"Missing handler for {name}")
    registry.register(name, handler)

for bare in DISABLED_COMMAND_NODES:
    name = f"fleetz_{bare}"
    registry.register(name, handlers.fleetz_disabled_command_handler)

# Internal helper used by playbooks / storm protection
registry.register("fleetz_event_coalesce", handlers.fleetz_event_coalesce_handler)
