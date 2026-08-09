"""Load generated Propreneur pack node and connector route catalogs (prompt 637)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_GEN = Path(__file__).resolve().parent


@lru_cache(maxsize=1)
def load_propreneur_pack_nodes() -> dict[str, Any]:
    path = _GEN / "propreneur_pack_nodes.json"
    if not path.is_file():
        raise FileNotFoundError(
            f"missing generated pack nodes at {path}; run "
            "bash keprix/scripts/regen-propreneur-agent-contract.sh"
        )
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_propreneur_connector_routes() -> dict[str, Any]:
    path = _GEN / "propreneur_connector_routes.json"
    if not path.is_file():
        raise FileNotFoundError(
            f"missing generated connector routes at {path}; run "
            "bash keprix/scripts/regen-propreneur-agent-contract.sh"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def clear_propreneur_generated_caches() -> None:
    load_propreneur_pack_nodes.cache_clear()
    load_propreneur_connector_routes.cache_clear()
