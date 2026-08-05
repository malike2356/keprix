"""Channel credential requirements registry (BotFather-style conversational config).

Pure data + helpers. No I/O. No network.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class ChannelField:
    key: str
    label: str
    description: str
    sensitive: bool
    optional: bool = False
    example: str | None = None
    env_key: str | None = None


@dataclass(frozen=True)
class ChannelRequirement:
    id: str
    name: str
    aliases: tuple[str, ...]
    description: str
    fields: tuple[ChannelField, ...]
    setup_docs: str | None = None
    # env: write encrypted store + ~/.keprix/.env (gateway may need restart)
    # db: reserved for future live adapter activation without env
    credential_type: str = "env"
    requires_restart: bool = True


def _f(
    key: str,
    label: str,
    description: str,
    *,
    sensitive: bool = False,
    optional: bool = False,
    example: str | None = None,
    env_key: str | None = None,
) -> ChannelField:
    return ChannelField(
        key=key,
        label=label,
        description=description,
        sensitive=sensitive,
        optional=optional,
        example=example,
        env_key=env_key or key.upper(),
    )


CHANNEL_REQUIREMENTS: tuple[ChannelRequirement, ...] = (
    ChannelRequirement(
        id="telegram",
        name="Telegram",
        aliases=("telegram", "tg", "tele"),
        description="Telegram Bot API messaging via BotFather token.",
        setup_docs="https://core.telegram.org/bots#how-do-i-create-a-bot",
        fields=(
            _f(
                "bot_token",
                "Bot token",
                "Token from @BotFather (looks like 123456:ABC...).",
                sensitive=True,
                example="123456789:ABC-DEF_placeholder_token",
                env_key="TELEGRAM_BOT_TOKEN",
            ),
        ),
    ),
    ChannelRequirement(
        id="discord",
        name="Discord",
        aliases=("discord", "dc"),
        description="Discord bot for guild and DM messaging.",
        setup_docs="https://discord.com/developers/applications",
        fields=(
            _f(
                "bot_token",
                "Bot token",
                "Bot token from the Discord Developer Portal.",
                sensitive=True,
                env_key="DISCORD_BOT_TOKEN",
            ),
            _f(
                "application_id",
                "Application ID",
                "Discord application (client) ID.",
                optional=True,
                env_key="DISCORD_APPLICATION_ID",
            ),
            _f(
                "guild_id",
                "Guild ID",
                "Optional default guild for slash command sync.",
                optional=True,
                env_key="DISCORD_GUILD_ID",
            ),
        ),
    ),
    ChannelRequirement(
        id="whatsapp_cloud",
        name="WhatsApp Cloud API",
        aliases=("whatsapp_cloud", "wa_cloud", "meta whatsapp", "whatsapp business"),
        description="Meta WhatsApp Cloud API (phone number id + access token).",
        setup_docs="https://developers.facebook.com/docs/whatsapp/cloud-api",
        fields=(
            _f(
                "access_token",
                "Access token",
                "System User permanent token for Cloud API.",
                sensitive=True,
                env_key="WHATSAPP_CLOUD_ACCESS_TOKEN",
            ),
            _f(
                "phone_number_id",
                "Phone number ID",
                "Graph API phone number id path component.",
                env_key="WHATSAPP_CLOUD_PHONE_NUMBER_ID",
            ),
            _f(
                "verify_token",
                "Verify token",
                "Shared secret for webhook hub.verify_token.",
                sensitive=True,
                env_key="WHATSAPP_CLOUD_VERIFY_TOKEN",
            ),
            _f(
                "app_secret",
                "App secret",
                "HMAC key for X-Hub-Signature-256 (recommended).",
                sensitive=True,
                optional=True,
                env_key="WHATSAPP_CLOUD_APP_SECRET",
            ),
        ),
    ),
    ChannelRequirement(
        id="whatsapp",
        name="WhatsApp (Baileys bridge)",
        aliases=("whatsapp", "wa", "baileys"),
        description="Local WhatsApp Web bridge via Baileys (QR pairing).",
        setup_docs="Run `keprix whatsapp` after enabling.",
        fields=(
            _f(
                "enabled",
                "Enable bridge",
                "Set to true to enable the WhatsApp bridge.",
                example="true",
                env_key="WHATSAPP_ENABLED",
            ),
            _f(
                "credentials_path",
                "Credentials path",
                "Optional path for bridge session data.",
                optional=True,
                env_key="WHATSAPP_CREDENTIALS_PATH",
            ),
        ),
    ),
    ChannelRequirement(
        id="slack",
        name="Slack",
        aliases=("slack",),
        description="Slack Socket Mode bot (bot token + app token).",
        setup_docs="https://api.slack.com/apps",
        fields=(
            _f(
                "bot_token",
                "Bot token",
                "xoxb- bot token for API calls.",
                sensitive=True,
                example="xoxb-...",
                env_key="SLACK_BOT_TOKEN",
            ),
            _f(
                "app_token",
                "App token",
                "xapp- app-level token for Socket Mode.",
                sensitive=True,
                example="xapp-...",
                env_key="SLACK_APP_TOKEN",
            ),
            _f(
                "signing_secret",
                "Signing secret",
                "Slack signing secret for request verification.",
                sensitive=True,
                optional=True,
                env_key="SLACK_SIGNING_SECRET",
            ),
        ),
    ),
    ChannelRequirement(
        id="signal",
        name="Signal",
        aliases=("signal",),
        description="signal-cli HTTP API bridge.",
        fields=(
            _f(
                "http_url",
                "signal-cli HTTP URL",
                "Base URL for signal-cli REST API.",
                example="http://127.0.0.1:8080",
                env_key="SIGNAL_HTTP_URL",
            ),
            _f(
                "account",
                "Signal account",
                "Phone number in E.164 form registered with signal-cli.",
                example="+15551234567",
                env_key="SIGNAL_ACCOUNT",
            ),
        ),
    ),
    ChannelRequirement(
        id="matrix",
        name="Matrix",
        aliases=("matrix", "element"),
        description="Matrix homeserver bot (token or password login).",
        fields=(
            _f(
                "homeserver",
                "Homeserver URL",
                "Homeserver base URL.",
                example="https://matrix.example.org",
                env_key="MATRIX_HOMESERVER",
            ),
            _f(
                "user_id",
                "User ID",
                "Full Matrix user id (@bot:server).",
                example="@keprix:example.org",
                env_key="MATRIX_USER_ID",
            ),
            _f(
                "access_token",
                "Access token",
                "Preferred auth: access token (skip password if set).",
                sensitive=True,
                optional=True,
                env_key="MATRIX_ACCESS_TOKEN",
            ),
            _f(
                "password",
                "Password",
                "Password login when no access token is available.",
                sensitive=True,
                optional=True,
                env_key="MATRIX_PASSWORD",
            ),
        ),
    ),
    ChannelRequirement(
        id="email",
        name="Email (IMAP + SMTP)",
        aliases=("email", "mail", "smtp", "imap"),
        description="Inbound IMAP and outbound SMTP for the agent mailbox.",
        fields=(
            _f(
                "address",
                "Email address",
                "Mailbox address for the agent.",
                example="agent@example.com",
                env_key="EMAIL_ADDRESS",
            ),
            _f(
                "password",
                "Password / app password",
                "Mailbox password or provider app password.",
                sensitive=True,
                env_key="EMAIL_PASSWORD",
            ),
            _f(
                "imap_host",
                "IMAP host",
                "IMAP server hostname.",
                example="imap.gmail.com",
                env_key="EMAIL_IMAP_HOST",
            ),
            _f(
                "imap_port",
                "IMAP port",
                "IMAP port (usually 993).",
                optional=True,
                example="993",
                env_key="EMAIL_IMAP_PORT",
            ),
            _f(
                "smtp_host",
                "SMTP host",
                "SMTP server hostname.",
                example="smtp.gmail.com",
                env_key="EMAIL_SMTP_HOST",
            ),
            _f(
                "smtp_port",
                "SMTP port",
                "SMTP port (usually 587).",
                optional=True,
                example="587",
                env_key="EMAIL_SMTP_PORT",
            ),
        ),
    ),
    ChannelRequirement(
        id="sms",
        name="SMS (Twilio)",
        aliases=("sms", "twilio", "text"),
        description="Twilio SMS send/receive.",
        setup_docs="https://www.twilio.com/docs/sms",
        fields=(
            _f(
                "account_sid",
                "Account SID",
                "Twilio Account SID.",
                sensitive=True,
                env_key="TWILIO_ACCOUNT_SID",
            ),
            _f(
                "auth_token",
                "Auth token",
                "Twilio Auth Token.",
                sensitive=True,
                env_key="TWILIO_AUTH_TOKEN",
            ),
            _f(
                "from_number",
                "From number",
                "E.164 Twilio phone number for outbound SMS.",
                example="+15551234567",
                env_key="TWILIO_PHONE_NUMBER",
            ),
        ),
    ),
    ChannelRequirement(
        id="teams",
        name="Microsoft Teams",
        aliases=("teams", "ms teams", "msteams", "microsoft teams"),
        description="Azure AD app credentials for Teams / Graph messaging.",
        fields=(
            _f(
                "client_id",
                "Client ID",
                "Azure AD application (client) ID.",
                env_key="TEAMS_CLIENT_ID",
            ),
            _f(
                "client_secret",
                "Client secret",
                "Azure AD client secret.",
                sensitive=True,
                env_key="TEAMS_CLIENT_SECRET",
            ),
            _f(
                "tenant_id",
                "Tenant ID",
                "Azure AD directory (tenant) ID.",
                env_key="TEAMS_TENANT_ID",
            ),
        ),
    ),
)

_BY_ID: dict[str, ChannelRequirement] = {c.id: c for c in CHANNEL_REQUIREMENTS}


def _normalize_alias(value: str) -> str:
    return " ".join(value.strip().lower().replace("_", " ").replace("-", " ").split())


_ALIAS_INDEX: dict[str, ChannelRequirement] = {}
for _req in CHANNEL_REQUIREMENTS:
    _ALIAS_INDEX[_normalize_alias(_req.id)] = _req
    _ALIAS_INDEX[_normalize_alias(_req.name)] = _req
    for _alias in _req.aliases:
        _ALIAS_INDEX[_normalize_alias(_alias)] = _req


def find_channel_by_alias(input_value: str) -> ChannelRequirement | None:
    if not input_value or not str(input_value).strip():
        return None
    return _ALIAS_INDEX.get(_normalize_alias(str(input_value)))


def get_channel(channel_id: str) -> ChannelRequirement | None:
    return _BY_ID.get((channel_id or "").strip().lower())


def list_channel_summaries() -> list[dict[str, object]]:
    return [
        {"id": c.id, "name": c.name, "aliases": list(c.aliases)}
        for c in CHANNEL_REQUIREMENTS
    ]


def get_required_fields(channel_id: str) -> list[ChannelField]:
    req = get_channel(channel_id)
    if req is None:
        return []
    return [f for f in req.fields if not f.optional]


def get_optional_fields(channel_id: str) -> list[ChannelField]:
    req = get_channel(channel_id)
    if req is None:
        return []
    return [f for f in req.fields if f.optional]


def get_sensitive_field_keys() -> set[str]:
    keys: set[str] = set()
    for req in CHANNEL_REQUIREMENTS:
        for fld in req.fields:
            if fld.sensitive:
                keys.add(fld.key)
                if fld.env_key:
                    keys.add(fld.env_key)
                keys.add(fld.key.lower())
                keys.add(fld.label.lower())
    return keys


def validate_credentials(
    channel_id: str,
    credentials: dict[str, str],
    *,
    allow_partial: bool = False,
) -> tuple[bool, str, dict[str, str]]:
    """Validate and normalize credential keys against the registry.

    Returns (ok, message, cleaned_credentials).
    """
    req = get_channel(channel_id) or find_channel_by_alias(channel_id)
    if req is None:
        return False, f"Unknown channel: {channel_id}", {}

    cleaned: dict[str, str] = {}
    known = {f.key: f for f in req.fields}
    for raw_key, raw_val in (credentials or {}).items():
        key = str(raw_key).strip()
        if key not in known:
            # Accept env_key aliases from callers
            matched = next((f for f in req.fields if f.env_key == key), None)
            if matched is None:
                return False, f"Unknown field '{key}' for {req.name}", {}
            key = matched.key
        val = str(raw_val).strip() if raw_val is not None else ""
        if not val:
            continue
        cleaned[key] = val

    if not allow_partial:
        missing = [f.key for f in req.fields if not f.optional and f.key not in cleaned]
        # Matrix: either access_token or password
        if req.id == "matrix":
            if "access_token" in cleaned:
                missing = [m for m in missing if m != "password"]
            elif "password" in cleaned:
                missing = [m for m in missing if m != "access_token"]
            else:
                missing = [m for m in missing if m not in {"access_token", "password"}]
                if "access_token" not in cleaned and "password" not in cleaned:
                    missing.append("access_token_or_password")
        if missing:
            return False, f"Missing required fields: {', '.join(missing)}", cleaned

    return True, "ok", cleaned


def credentials_to_env(channel_id: str, credentials: dict[str, str]) -> dict[str, str]:
    req = get_channel(channel_id)
    if req is None:
        return {}
    out: dict[str, str] = {}
    by_key = {f.key: f for f in req.fields}
    for key, value in credentials.items():
        fld = by_key.get(key)
        if fld is None or not value:
            continue
        env_name = fld.env_key or key.upper()
        out[env_name] = value
    return out


def iter_requirements() -> Iterable[ChannelRequirement]:
    return CHANNEL_REQUIREMENTS
