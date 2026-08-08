# keprix - Prompt 09: Agent-Managed Credential Setup

## Purpose

Make keprix able to configure itself when a user supplies the required credentials through chat, web UI, CLI, or an approved channel. Users and admins should not need to repeatedly edit `.env` files on the server for normal setup tasks.

The goal is near-full agent-operated setup:

- The user tells keprix what they want to connect.
- keprix asks only for the missing credentials or choices.
- The user supplies the credential securely.
- keprix validates it.
- keprix stores it in the vault.
- keprix updates runtime configuration.
- keprix tests the integration.
- keprix reports what is now working and what still needs action.

`.env` files may still exist for bootstrap and emergency recovery, but they should not be the default operator workflow.

## Relationship To Earlier Prompts

This prompt extends:

- Prompt 08: encrypted vault, auth, backup, redaction, audit.
- Prompt 02: security foundation and secret handling.
- Prompt 16: self-configuration and auto-repair.
- Prompt 23: slash commands.
- Prompt 27: localization, voice, and channel-aware input.

Prompt 16 handles runtime repair and environment discovery. This prompt handles user-guided credential setup and agent-operated configuration.

## Scope

Implement:

- Secure credential intake through web UI, CLI, TUI, Telegram, Discord, Slack, Matrix, and WebChat where supported.
- A typed setup registry for services such as LLM providers, messaging channels, email, calendar, storage, vector databases, search APIs, Scout, speech providers, translation providers, and payment providers.
- Vault-first secret storage.
- Runtime configuration overlays that do not require hand-editing `.env`.
- Validation probes for every supported credential type.
- Natural-language setup flows, for example "connect my OpenAI key" or "set up Telegram".
- Confirmation gates before enabling external actions.
- Redaction in logs, chat history, audit records, traces, screenshots, and error messages.
- Key rotation, disabling, deletion, and health checks.
- Admin policy controls for which users can add which credential types.
- Tests for secret handling, validation, audit, channel safety, and config reload.

## Design Principle

keprix should treat `.env` as bootstrap only.

Use this order of precedence:

1. Emergency runtime overrides set by an owner.
2. Vault-backed active configuration set by the agent.
3. Workspace configuration stored in the database.
4. Generated config from Prompt 16 discovery.
5. Bootstrap `.env`.
6. Built-in safe defaults.

The app must keep working when no `.env` exists except the minimum bootstrap values required to start the process and unlock local storage.

## Output Paths

Use these target paths unless the codebase evolves before implementation:

```text
keprix/backend/setup/
  __init__.py
  registry.py
  flows.py
  schemas.py
  permissions.py
  validation.py
  runtime_apply.py
  audit.py
  redaction.py
  providers/
    __init__.py
    llm.py
    telegram.py
    discord.py
    slack.py
    email.py
    calendar.py
    storage.py
    vector_db.py
    search.py
    scout.py
    speech.py
    translation.py
    payments.py

keprix/backend/api/setup.py
keprix/backend/cli/setup_commands.py
keprix/backend/gateway/secure_input.py
keprix/backend/config/runtime_config.py
keprix/tests/setup/
```

## Setup Item Contract

Create a typed setup item contract:

```python
class SetupItem:
    id: str
    name: str
    category: str
    description: str
    required_role: str
    required_fields: list[CredentialField]
    optional_fields: list[CredentialField]
    validation_mode: str
    enables_capabilities: list[str]
    risks: list[str]
    confirmation_required: bool
    handler: SetupHandler
```

Credential fields must support:

- `name`
- `label`
- `secret`
- `required`
- `format_hint`
- `validation_regex`
- `redaction_strategy`
- `storage_scope`
- `rotation_supported`

Never store secret plaintext in the setup flow state. The flow state may store a vault item reference only.

## Credential Intake Flow

For each credential setup:

1. Identify the requested service from natural language or slash command.
2. Check the user's role and workspace policy.
3. Explain what credential is needed and where it will be stored.
4. Ask the user to submit the credential through a secure input path.
5. Redact the credential immediately after receipt.
6. Store the credential in the vault.
7. Validate the credential with a minimal probe.
8. If valid, create or update the active runtime config.
9. Reload the affected component without restarting the whole server where possible.
10. Run a health check.
11. Log the setup action without plaintext secret values.
12. Tell the user exactly what is now enabled.

If validation fails, keep the vault item disabled by default and explain the failure without echoing the secret.

## Secure Input Paths

### Web UI

- Use password-style fields for secrets.
- Submit directly to a credential endpoint over HTTPS.
- Do not place secrets in URLs, query strings, local storage, screenshots, or browser logs.
- Show a one-time "received" state, then hide the value permanently.

### CLI And TUI

- Read secrets from an interactive hidden prompt where possible.
- Support `--from-stdin` for automation.
- Warn when a user passes a secret through command arguments.
- Never write secrets to shell history.

### Telegram, Discord, Slack, Matrix, And WebChat

- Prefer private chats, ephemeral messages, modals, or secure web handoff links.
- In public or group channels, refuse to accept raw secrets and provide a secure handoff link.
- Delete raw secret messages where the platform allows it.
- Redact secrets before they enter long-term chat memory.
- If deletion is not possible, warn the user and rotate the credential after setup if the provider supports rotation.

## Runtime Configuration

Add a runtime config layer that can resolve values from the vault without writing secrets to `.env`.

Example:

```yaml
llm:
  primary_provider: openai
  providers:
    openai:
      api_key_ref: vault://workspace/default/llm/openai/main
      enabled: true
      default_model: gpt-4.1-mini
    deepseek:
      api_key_ref: vault://workspace/default/llm/deepseek/main
      enabled: false

channels:
  telegram:
    bot_token_ref: vault://workspace/default/channel/telegram/bot-token
    allowed_users:
      - "123456789"
    enabled: true
```

The runtime loader resolves `vault://` references at use time and keeps decrypted values in memory only as long as needed.

## Supported Setup Flows

Ship v1 setup handlers for:

| Setup | Example User Request | Validation |
| --- | --- | --- |
| OpenAI API key | "Use this OpenAI key for models" | Minimal model list or low-cost completion probe |
| Anthropic API key | "Connect Claude" | Model list or messages probe |
| DeepSeek API key | "Add DeepSeek as fallback" | Chat probe |
| Gemini API key | "Set up Gemini" | Model list or generate probe |
| Groq API key | "Add Groq for fast inference" | Model list or completion probe |
| Telegram bot token | "Connect my Telegram bot" | `getMe` and webhook test |
| Discord bot token | "Connect Discord" | Gateway identity check |
| Slack app credentials | "Connect Slack" | Signing secret check and auth test |
| Email IMAP and SMTP | "Connect this mailbox" | Login and send test to owner-approved address |
| CalDAV calendar | "Connect my calendar" | Principal discovery and read-only event probe |
| S3-compatible storage | "Use this bucket for files" | List, write, read, delete test object |
| Vector database | "Connect Qdrant" | Collection create and delete test |
| Search API | "Enable web search" | Low-cost query probe |
| Scout enrollment | "Connect this keprix to Scout" | Enrollment handshake |
| Speech provider | "Enable voice transcription" | Short test audio transcription |
| Translation provider | "Enable African language translation" | Known phrase translation probe |
| Payment provider | "Connect Stripe" | Account identity check, no charge |

Each handler must declare the exact capabilities it enables.

## Natural Language Examples

Support user instructions like:

- "Carina, use this OpenAI key as the main model provider."
- "Set Telegram up for me. Here is the bot token."
- "Connect Scout to this workspace."
- "Add this DeepSeek key but only use it as fallback."
- "Turn on voice transcription for Twi and Swahili."
- "Use this translation provider for Yoruba, Igbo, Hausa, and Swahili."
- "Rotate the Telegram token."
- "Disable the old OpenAI key."
- "Show me which services are configured."

For secrets in chat, the agent must redirect to a secure input path when the channel is unsafe.

## Slash Commands

Prompt 23 owns the slash command registry. Add these handlers:

| Command | Purpose |
| --- | --- |
| `/setup` | Show setup status and available setup flows. |
| `/setup start <service>` | Start guided setup for a service. |
| `/setup status` | Show configured services without revealing secrets. |
| `/setup test <service>` | Re-run validation probes. |
| `/setup disable <service>` | Disable a configured service after confirmation. |
| `/setup rotate <service>` | Start credential rotation. |
| `/setup delete <service>` | Delete a credential after owner confirmation. |
| `/setup policy` | Show who can configure which services. |

Risky commands require confirmation and owner or admin role depending on service policy.

## Permissions

Default permission model:

- `viewer`: can view setup status without secret metadata.
- `operator`: can start non-secret diagnostic setup flows.
- `admin`: can add or update normal service credentials.
- `owner`: can add payment credentials, Scout enrollment keys, security-sensitive channel credentials, delete credentials, and change setup policy.

Workspace policy must allow stricter rules, for example "only owner can add LLM keys" or "no cloud providers allowed".

## Audit Log

Create a setup audit table:

```sql
CREATE TABLE setup_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    service_id TEXT NOT NULL,
    action TEXT NOT NULL,
    status TEXT NOT NULL,
    vault_item_id TEXT,
    capability_enabled TEXT,
    validation_provider TEXT,
    validation_summary TEXT,
    risk_level TEXT NOT NULL DEFAULT 'medium',
    confirmation_required BOOLEAN NOT NULL DEFAULT FALSE,
    confirmation_actor TEXT,
    error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

Audit records must never include plaintext secrets or full credential fingerprints. Store only short non-sensitive fingerprints such as provider name, last 4 characters where safe, created time, and vault item id.

## API Surface

Expose:

```text
GET  /api/setup/catalog
GET  /api/setup/status
POST /api/setup/start
POST /api/setup/secure-input
POST /api/setup/validate
POST /api/setup/apply
POST /api/setup/test
POST /api/setup/disable
POST /api/setup/rotate
POST /api/setup/delete
GET  /api/setup/audit
GET  /api/setup/policy
POST /api/setup/policy
```

All endpoints require authentication. Secret intake endpoints require CSRF protection or channel signature verification where applicable.

## Redaction Rules

Add redaction before any logging, tracing, memory write, model call, or audit write.

Redact:

- API keys.
- Bot tokens.
- OAuth secrets.
- Refresh tokens.
- Passwords.
- Private keys.
- Session cookies.
- Authorization headers.
- Database URLs with passwords.
- SMTP and IMAP passwords.
- Payment provider secret keys.

Use pattern-based redaction plus field-aware redaction. Field-aware redaction must win.

## Model Safety

The agent must not send raw credentials to an LLM unless the local policy explicitly allows it and the model is local and trusted. Normal setup does not require the model to inspect the secret. The setup handler should validate credentials through provider APIs directly.

When a user pastes a credential into a normal chat message:

1. Detect the likely secret.
2. Stop normal agent reasoning for that message.
3. Move the value into secure intake if possible.
4. Redact it from the conversation transcript.
5. Continue with the setup flow.

## Recovery And Bootstrap

Support a minimal bootstrap mode:

- First run starts without provider API keys.
- Local setup UI is available.
- Owner account can be created.
- Vault can be initialized.
- The user can add the first LLM provider through secure setup.
- After validation, keprix can use that provider immediately.

If the vault is locked or unavailable, setup must pause and guide the owner to unlock or repair the vault. Do not fall back to writing plaintext secrets into `.env`.

## Tests

Add tests for:

- A user can add an OpenAI API key through secure input and the active LLM config updates.
- A Telegram bot token can be validated with `getMe` and enabled without editing `.env`.
- Public group chat refuses raw secret intake and returns a secure handoff.
- Secret values are redacted before chat memory writes.
- Secret values are redacted before logs and audit records.
- Invalid credentials are stored disabled or discarded according to policy.
- Runtime config resolves `vault://` references and does not expose plaintext in status output.
- Admin can rotate a key and the old key is disabled.
- Owner confirmation is required before deleting a credential.
- Workspace policy can block cloud provider setup.
- Setup status lists services and health without revealing secrets.
- No credential is passed to an LLM during setup validation.
- Restart preserves vault-backed configuration.
- Bootstrap first-run can add the first provider without manual `.env` edits.

## Acceptance Criteria

- keprix can be installed with minimal bootstrap config.
- A user can tell the agent to connect a provider, supply a credential securely, and have the provider enabled without touching server `.env` files.
- Credential values are stored in the vault, not plaintext runtime files.
- Runtime components can read active configuration from vault-backed references.
- Setup flows work from web UI and CLI, with safe channel behavior for chat platforms.
- Every setup action is permission-checked and audited.
- Secret values are redacted from logs, chat history, traces, model prompts, and audit rows.
- The agent can validate, enable, disable, rotate, and delete service credentials.
- The agent can report setup status in plain language without exposing secrets.
- `.env` remains available for bootstrap and emergency recovery, but normal setup does not require server file editing.
