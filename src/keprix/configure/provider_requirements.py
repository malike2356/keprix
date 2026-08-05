"""Provider / BYOK requirements registry for conversational config (Wave 2a)."""

from __future__ import annotations

from dataclasses import dataclass

from keprix.api.provider_settings import (
    PRIORITY_UI_IDS,
    AdminProviderSpec,
    get_admin_provider_specs,
)


@dataclass(frozen=True)
class ConfigField:
    key: str
    label: str
    description: str
    sensitive: bool
    optional: bool = False
    example: str | None = None
    env_key: str | None = None


@dataclass(frozen=True)
class ProviderRequirement:
    id: str
    name: str
    aliases: tuple[str, ...]
    description: str
    fields: tuple[ConfigField, ...]
    setup_docs: str | None = None
    credential_type: str = "env"
    requires_restart: bool = False
    env_key: str | None = None


_EXTRA_ALIASES: dict[str, tuple[str, ...]] = {
    "openai": ("openai", "gpt", "chatgpt"),
    "anthropic": ("anthropic", "claude"),
    "google": ("google", "gemini", "google ai"),
    "deepseek": ("deepseek",),
    "groq": ("groq",),
    "openrouter": ("openrouter", "open router"),
    "mistral": ("mistral",),
    "xai": ("xai", "grok", "x.ai"),
    "ollama": ("ollama", "local", "local llm"),
    "lmstudio": ("lmstudio", "lm studio"),
}


def _fields_for_spec(spec: AdminProviderSpec) -> tuple[ConfigField, ...]:
    fields: list[ConfigField] = []
    if spec.ui_id == "ollama":
        fields.append(
            ConfigField(
                key="host",
                label="Ollama host",
                description="Ollama base URL (default http://localhost:11434).",
                sensitive=False,
                optional=True,
                example="http://localhost:11434",
                env_key="OLLAMA_HOST",
            )
        )
    elif spec.env_key:
        fields.append(
            ConfigField(
                key="api_key",
                label="API key",
                description=f"API key for {spec.label} (stored in {spec.env_key}).",
                sensitive=True,
                example="sk-... (paste your key; never share it in chat logs)",
                env_key=spec.env_key,
            )
        )
    fields.append(
        ConfigField(
            key="default_model",
            label="Default model",
            description=f"Optional default model id (example: {spec.default_model or 'provider-default'}).",
            sensitive=False,
            optional=True,
            example=spec.default_model or None,
            env_key=f"KEPRIX_{spec.ui_id.upper().replace('-', '_')}_DEFAULT_MODEL",
        )
    )
    return tuple(fields)


def _aliases_for(spec: AdminProviderSpec) -> tuple[str, ...]:
    extras = _EXTRA_ALIASES.get(spec.ui_id, ())
    base = (spec.ui_id, spec.label.lower(), *(extras or ()))
    # unique preserve order
    seen: set[str] = set()
    out: list[str] = []
    for a in base:
        n = " ".join(str(a).strip().lower().split())
        if n and n not in seen:
            seen.add(n)
            out.append(n)
    return tuple(out)


def build_provider_requirements() -> tuple[ProviderRequirement, ...]:
    specs = list(get_admin_provider_specs())
    # Prefer priority providers first for conversational discovery
    priority = {ui: i for i, ui in enumerate(PRIORITY_UI_IDS)}
    specs.sort(key=lambda s: (priority.get(s.ui_id, 999), s.label.lower()))
    reqs: list[ProviderRequirement] = []
    for spec in specs:
        fields = _fields_for_spec(spec)
        if not fields:
            continue
        # Skip providers with neither api_key nor ollama host path
        if spec.ui_id != "ollama" and not spec.env_key:
            continue
        reqs.append(
            ProviderRequirement(
                id=spec.ui_id,
                name=spec.label,
                aliases=_aliases_for(spec),
                description=f"Configure {spec.label} API access and optional default model.",
                fields=fields,
                env_key=spec.env_key,
                requires_restart=False,
            )
        )
    return tuple(reqs)


PROVIDER_REQUIREMENTS: tuple[ProviderRequirement, ...] = build_provider_requirements()

_BY_ID: dict[str, ProviderRequirement] = {p.id: p for p in PROVIDER_REQUIREMENTS}


def _normalize(value: str) -> str:
    return " ".join(value.strip().lower().replace("_", " ").replace("-", " ").split())


_ALIAS_INDEX: dict[str, ProviderRequirement] = {}
for _req in PROVIDER_REQUIREMENTS:
    _ALIAS_INDEX[_normalize(_req.id)] = _req
    _ALIAS_INDEX[_normalize(_req.name)] = _req
    for _alias in _req.aliases:
        _ALIAS_INDEX[_normalize(_alias)] = _req


def find_provider_by_alias(input_value: str) -> ProviderRequirement | None:
    if not input_value or not str(input_value).strip():
        return None
    return _ALIAS_INDEX.get(_normalize(str(input_value)))


def get_provider(provider_id: str) -> ProviderRequirement | None:
    return _BY_ID.get((provider_id or "").strip().lower()) or find_provider_by_alias(provider_id or "")


def list_provider_summaries() -> list[dict[str, object]]:
    return [{"id": p.id, "name": p.name, "aliases": list(p.aliases)} for p in PROVIDER_REQUIREMENTS]


def get_required_fields(provider_id: str) -> list[ConfigField]:
    req = get_provider(provider_id)
    if req is None:
        return []
    return [f for f in req.fields if not f.optional]


def get_optional_fields(provider_id: str) -> list[ConfigField]:
    req = get_provider(provider_id)
    if req is None:
        return []
    return [f for f in req.fields if f.optional]


def get_sensitive_provider_field_keys() -> set[str]:
    keys: set[str] = set()
    for req in PROVIDER_REQUIREMENTS:
        for fld in req.fields:
            if fld.sensitive:
                keys.add(fld.key)
                keys.add(fld.label.lower())
                if fld.env_key:
                    keys.add(fld.env_key)
    keys.update({"api_key", "api key", "openai_api_key", "anthropic_api_key"})
    return keys


def validate_provider_credentials(
    provider_id: str,
    credentials: dict[str, str],
) -> tuple[bool, str, dict[str, str]]:
    req = get_provider(provider_id)
    if req is None:
        return False, f"Unknown provider: {provider_id}", {}
    cleaned: dict[str, str] = {}
    known = {f.key: f for f in req.fields}
    for raw_key, raw_val in (credentials or {}).items():
        key = str(raw_key).strip()
        matched = known.get(key) or next((f for f in req.fields if f.env_key == key), None)
        if matched is None:
            return False, f"Unknown field '{key}' for {req.name}", {}
        val = str(raw_val).strip() if raw_val is not None else ""
        if not val:
            continue
        cleaned[matched.key] = val

    if req.id == "ollama":
        # host optional; nothing strictly required to mark "configured" beyond reachability
        return True, "ok", cleaned

    missing = [f.key for f in req.fields if not f.optional and f.key not in cleaned]
    if missing:
        return False, f"Missing required fields: {', '.join(missing)}", cleaned
    return True, "ok", cleaned
