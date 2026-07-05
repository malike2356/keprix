"""Admin settings provider discovery and persistence."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from keprix.api.chat_inference import PROVIDER_DEFAULT_MODELS

REGISTRY_ALIASES: dict[str, str] = {
    "google": "gemini",
    "openai": "openai-api",
}

UI_ID_OVERRIDES: dict[str, str] = {
    "openai-api": "openai",
    "gemini": "google",
}

PRIORITY_UI_IDS: tuple[str, ...] = (
    "deepseek",
    "anthropic",
    "openai",
    "google",
    "groq",
    "xai",
    "openrouter",
    "mistral",
    "minimax",
    "kimi-coding",
    "zai",
    "ollama",
    "lmstudio",
    "ollama-cloud",
    "huggingface",
    "nvidia",
    "opencode-zen",
    "opencode-go",
    "kilocode",
)

@dataclass(frozen=True)
class AdminProviderSpec:
    ui_id: str
    label: str
    registry_id: str | None
    env_key: str | None
    default_model: str
    env_keys: tuple[str, ...] = ()


SUPPLEMENTAL_SPECS: tuple[AdminProviderSpec, ...] = (
    AdminProviderSpec("groq", "Groq", None, "GROQ_API_KEY", "llama-3.3-70b"),
    AdminProviderSpec("openrouter", "OpenRouter", None, "OPENROUTER_API_KEY", "openrouter/auto"),
    AdminProviderSpec("mistral", "Mistral", None, "MISTRAL_API_KEY", "mistral-large-latest"),
    AdminProviderSpec("ollama", "Ollama (local)", None, None, "llama3.2"),
)


def registry_provider_id(provider_id: str) -> str:
    return REGISTRY_ALIASES.get(provider_id, provider_id)


@lru_cache(maxsize=1)
def get_admin_provider_specs() -> tuple[AdminProviderSpec, ...]:
    try:
        from keprix_cli.auth import PROVIDER_REGISTRY
    except Exception:
        return SUPPLEMENTAL_SPECS

    specs: list[AdminProviderSpec] = []
    seen_ui_ids: set[str] = set()

    for registry_id, pconfig in PROVIDER_REGISTRY.items():
        if pconfig.auth_type != "api_key":
            continue
        ui_id = UI_ID_OVERRIDES.get(registry_id, registry_id)
        if ui_id in seen_ui_ids:
            continue
        env_keys = tuple(pconfig.api_key_env_vars or ())
        env_key = env_keys[0] if env_keys else None
        default_model = (
            PROVIDER_DEFAULT_MODELS.get(ui_id)
            or PROVIDER_DEFAULT_MODELS.get(registry_id)
            or ""
        )
        specs.append(
            AdminProviderSpec(
                ui_id=ui_id,
                label=pconfig.name,
                registry_id=registry_id,
                env_key=env_key,
                default_model=default_model,
                env_keys=env_keys,
            )
        )
        seen_ui_ids.add(ui_id)

    for supplemental in SUPPLEMENTAL_SPECS:
        if supplemental.ui_id not in seen_ui_ids:
            specs.append(supplemental)
            seen_ui_ids.add(supplemental.ui_id)

    priority = {ui_id: index for index, ui_id in enumerate(PRIORITY_UI_IDS)}
    specs.sort(key=lambda spec: (priority.get(spec.ui_id, 999), spec.label.lower()))
    return tuple(specs)


def admin_provider_catalog() -> list[dict[str, str]]:
    return [{"id": spec.ui_id, "label": spec.label} for spec in get_admin_provider_specs()]


def _spec_for_ui_id(provider_id: str) -> AdminProviderSpec | None:
    for spec in get_admin_provider_specs():
        if spec.ui_id == provider_id:
            return spec
    return None


def _registry_status(registry_id: str) -> dict[str, Any]:
    try:
        from keprix_cli.auth import get_api_key_provider_status

        return get_api_key_provider_status(registry_id)
    except Exception:
        return {"configured": False}


def _env_keys_configured(env_keys: tuple[str, ...]) -> bool:
    return any(os.getenv(key, "").strip() for key in env_keys)


def _spec_connected(spec: AdminProviderSpec) -> tuple[bool, str | None]:
    if spec.ui_id == "ollama":
        return _ollama_status()

    if spec.registry_id:
        status = _registry_status(spec.registry_id)
        if status.get("configured"):
            model = PROVIDER_DEFAULT_MODELS.get(spec.ui_id, spec.default_model) or spec.default_model
            return True, model or "configured"

    keys = spec.env_keys or ((spec.env_key,) if spec.env_key else ())
    if keys and _env_keys_configured(keys):
        model = PROVIDER_DEFAULT_MODELS.get(spec.ui_id, spec.default_model) or spec.default_model
        return True, model or "configured"

    return False, None


def _ollama_status() -> tuple[bool, str | None]:
    host = os.getenv("OLLAMA_HOST", os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
    if host.endswith("/v1"):
        host = host[:-3]
    try:
        import httpx

        response = httpx.get(f"{host}/api/tags", timeout=2.0)
        if response.status_code == 200:
            display = host.replace("https://", "").replace("http://", "")
            return True, display
    except Exception:
        pass
    return False, None


def provider_settings_snapshot() -> dict[str, dict[str, Any]]:
    default_provider = os.getenv("KEPRIX_DEFAULT_PROVIDER", "").strip().lower()
    snapshot: dict[str, dict[str, Any]] = {}

    for spec in get_admin_provider_specs():
        connected, model = _spec_connected(spec)
        snapshot[spec.ui_id] = {
            "connected": connected,
            "default_model": model if connected else None,
            "is_default": spec.ui_id == default_provider,
        }

    return snapshot


def _resolve_env_file() -> Path | None:
    explicit = os.getenv("KEPRIX_ENV_FILE", "").strip()
    if explicit:
        return Path(explicit)
    project_env = Path.cwd() / ".env"
    if project_env.exists():
        return project_env
    try:
        from keprix_cli.config import get_env_path

        path = get_env_path()
        return path if path.exists() else None
    except Exception:
        return None


def _upsert_env_file(path: Path, key: str, value: str) -> None:
    lines: list[str] = []
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    key_prefix = f"{key}="
    replaced = False
    output: list[str] = []
    for line in lines:
        if line.startswith(key_prefix):
            output.append(f"{key}={value}\n")
            replaced = True
        else:
            output.append(line if line.endswith("\n") else f"{line}\n")
    if not replaced:
        if output and not output[-1].endswith("\n"):
            output[-1] = output[-1] + "\n"
        output.append(f"{key}={value}\n")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(output), encoding="utf-8")


def persist_env_value(key: str, value: str) -> None:
    cleaned = value.replace("\n", "").replace("\r", "")
    os.environ[key] = cleaned
    env_file = _resolve_env_file()
    if env_file is not None:
        _upsert_env_file(env_file, key, cleaned)


def save_provider_settings(
    provider_id: str,
    *,
    api_key: str | None = None,
    default_model: str | None = None,
) -> dict[str, Any]:
    spec = _spec_for_ui_id(provider_id)
    if spec is None:
        raise KeyError(provider_id)

    if api_key and spec.env_key:
        persist_env_value(spec.env_key, api_key)

    if default_model:
        model_env_key = f"KEPRIX_{spec.ui_id.upper().replace('-', '_')}_DEFAULT_MODEL"
        persist_env_value(model_env_key, default_model)

    if api_key and not os.getenv("KEPRIX_DEFAULT_PROVIDER"):
        persist_env_value("KEPRIX_DEFAULT_PROVIDER", spec.ui_id)

    from keprix.api.chat_inference import invalidate_provider_cache
    invalidate_provider_cache()

    return provider_settings_snapshot()[provider_id]


def test_provider_settings(provider_id: str) -> dict[str, Any]:
    snapshot = provider_settings_snapshot()
    entry = snapshot.get(provider_id)
    if not entry:
        return {"ok": False, "message": "Provider not found"}
    if entry.get("connected"):
        label = next((spec.label for spec in get_admin_provider_specs() if spec.ui_id == provider_id), provider_id)
        model = entry.get("default_model") or "configured"
        return {"ok": True, "message": f"{label} connected ({model})"}
    return {"ok": False, "message": "Not configured"}
