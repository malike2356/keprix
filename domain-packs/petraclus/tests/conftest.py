"""Shared pytest helpers for the Petraclus pack."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

PACK_ROOT = Path(__file__).resolve().parents[1]
_MODULE_NAME = "petraclus_http_app"


def load_app():
    """Load http_app once under a stable module name for Pydantic rebuild."""
    if str(PACK_ROOT) not in sys.path:
        sys.path.insert(0, str(PACK_ROOT))
    if _MODULE_NAME in sys.modules and hasattr(sys.modules[_MODULE_NAME], "app"):
        return sys.modules[_MODULE_NAME].app
    spec = importlib.util.spec_from_file_location(_MODULE_NAME, PACK_ROOT / "http_app.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[_MODULE_NAME] = module
    spec.loader.exec_module(module)
    for name in ("SessionIn", "InvokeIn", "JobIn", "EventIn", "ApprovalIn", "ProvisionIn"):
        model = getattr(module, name, None)
        if model is not None and hasattr(model, "model_rebuild"):
            model.model_rebuild()
    return module.app


@pytest.fixture
def client() -> TestClient:
    return TestClient(load_app())
