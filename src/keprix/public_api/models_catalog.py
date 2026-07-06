"""Model catalog for the public OpenAI-compatible API."""

from __future__ import annotations


def list_public_models() -> list[tuple[str, str]]:
    models: list[tuple[str, str]] = [
        ("keprix", "keprix"),
        ("keprix-fast", "keprix"),
        ("keprix-embed", "keprix"),
    ]
    try:
        from gateway.run import _load_gateway_config, _resolve_gateway_model

        configured = _resolve_gateway_model(_load_gateway_config())
        if configured and configured not in {model_id for model_id, _ in models}:
            models.insert(0, (configured, "keprix"))
    except Exception:
        pass
    return models
