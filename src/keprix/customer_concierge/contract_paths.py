"""Resolve Customer Concierge v1 contract package paths (Prompt 629).

Prefers vendored ``keprix/contracts/customer-concierge-v1/``. Falls back to the
shared workspace mirror. Never imports Carina.
"""

from __future__ import annotations

from pathlib import Path

_KEPRIX_ROOT = Path(__file__).resolve().parents[3]
_VENDORED = _KEPRIX_ROOT / "contracts" / "customer-concierge-v1"
_SHARED = Path("/opt/lampp/htdocs/verlox/shared/contracts/customer-concierge-v1")


def contract_root() -> Path:
    if (_VENDORED / "contract.json").is_file():
        return _VENDORED
    if (_SHARED / "contract.json").is_file():
        return _SHARED
    raise FileNotFoundError(
        "Customer Concierge v1 contract not found under keprix/contracts or shared/contracts"
    )


def schemas_dir() -> Path:
    return contract_root() / "schemas"


def fixtures_dir() -> Path:
    return contract_root() / "fixtures" / "synthetic"


def load_manifest() -> dict:
    import json

    return json.loads((contract_root() / "contract.json").read_text(encoding="utf-8"))
