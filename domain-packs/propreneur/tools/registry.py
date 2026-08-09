"""Load and validate Propreneur Aiva tool contract for the domain pack."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_PACK_ROOT = Path(__file__).resolve().parents[1]
_TOOLS_CONTRACT = _PACK_ROOT / "contracts" / "propreneur-aiva-tools.v1.json"
_RISK_CONTRACT = _PACK_ROOT / "contracts" / "propreneur-action-risk.v1.json"
_EXPECTED_TOOLS_VERSION = "1.3.0"


class PropreneurContractVersionError(ValueError):
    pass


def load_tools_contract(*, expected_version: str = _EXPECTED_TOOLS_VERSION) -> dict[str, Any]:
    raw = json.loads(_TOOLS_CONTRACT.read_text(encoding="utf-8"))
    if raw.get("contract") != "propreneur-aiva-tools":
        raise PropreneurContractVersionError(f"unexpected contract: {raw.get('contract')}")
    version = str(raw.get("version") or "")
    compatible = list(raw.get("compatible_versions") or [])
    if version != expected_version and expected_version not in compatible:
        raise PropreneurContractVersionError(
            f"incompatible tools contract {version}; expected {expected_version}"
        )
    tools = raw.get("tools") or []
    if not isinstance(tools, list) or not tools:
        raise PropreneurContractVersionError("tools list empty")
    return raw


def list_tool_names() -> list[str]:
    return [str(t["name"]) for t in load_tools_contract()["tools"]]


def load_action_risk_contract() -> dict[str, Any]:
    raw = json.loads(_RISK_CONTRACT.read_text(encoding="utf-8"))
    if str(raw.get("version")) != "1.0.0":
        raise PropreneurContractVersionError("incompatible action-risk version")
    return raw
