"""Tool registry: discovers, stores, and serves tools to the agent engine.

Built-in tools are registered at import time via register().
Synthesised tools (Prompt 28) are hot-loaded at runtime via load_generated().

The registry is a process-level singleton - one instance per Keprix process.
"""

from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path
from typing import Any

from keprix.tools.base import BaseTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    _instance: ToolRegistry | None = None

    def __new__(cls) -> ToolRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools: dict[str, BaseTool] = {}
        return cls._instance

    def register(self, tool: BaseTool) -> None:
        if tool.name in self._tools:
            logger.debug("Overwriting existing tool: %s", tool.name)
        self._tools[tool.name] = tool
        logger.debug("Registered tool: %s", tool.name)

    def unregister(self, name: str) -> bool:
        if name in self._tools:
            del self._tools[name]
            logger.info("Unregistered tool: %s", name)
            return True
        return False

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def all(self) -> list[BaseTool]:
        return list(self._tools.values())

    def to_llm_schemas(self) -> list[dict[str, Any]]:
        return [t.to_llm_schema() for t in self._tools.values()]

    def load_generated(self, tools_dir: Path) -> int:
        """Hot-load all approved synthesised tools from the generated/ directory.

        Each .py file in tools_dir is expected to define exactly one class that
        subclasses BaseTool. Returns the count of tools loaded.
        """
        loaded = 0
        for path in sorted(tools_dir.glob("*.py")):
            if path.name.startswith("_"):
                continue
            try:
                module_name = f"keprix.tools.generated.{path.stem}"
                spec = importlib.util.spec_from_file_location(module_name, path)
                if spec is None or spec.loader is None:
                    continue
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, BaseTool)
                        and attr is not BaseTool
                    ):
                        self.register(attr())
                        loaded += 1
            except Exception as exc:
                logger.error("Failed to load generated tool %s: %s", path.name, exc)
        return loaded
