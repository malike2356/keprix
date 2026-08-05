# keprix - Coder Standards
# Stack: Python / FastAPI / self-hosted agent OS
# Read this before writing any prompt, tool, or backend code.
# These standards layer on top of ENGINEERING-PILLARS.md - read that first.

---

## 0. READ FIRST

`ENGINEERING-PILLARS.md` governs every design decision. These standards are the implementation-level translation of those pillars.

Pillars summary (know them):
1. Security first - always.
2. AI woven in from foundation, not bolted on.
3. No emojis, no fluff, direct but warm.
4. No em dashes, no en dashes.
5. Cause no risk to data, information, assets, or finance.
6. Ethical, within the bounds of human ethics.
7. Compliance with law and regulation.

---

## 1. PRODUCTION MINDSET

keprix is self-hosted. Your users run it on their own machines, their own servers, their own data. Production for them is the day they install it.

"Your users don't care if it works on your machine. They care if it works on theirs."

Every tool, every endpoint, every mutation must:
- Work on Python 3.10+, not just the version in your dev container.
- Fail safely. If a mutation fails, the user's system must be left in a valid state. Never partially install a tool and leave it broken.
- Log enough to understand what went wrong. Never log credentials, API keys, or personal data.
- Use environment variables for all configuration. Nothing hard-coded.

Pre-flight checks before any feature is considered done:
- Does it handle the case where the AI provider is unreachable?
- Does it handle the case where the mutation sandbox produces an error?
- Does it handle the case where the user has no network?
- Does it produce a clear, human-readable error message in every failure case?

---

## 2. SECURITY - THE 5 MISTAKES WE DO NOT MAKE

1. TRUST THE FRONTEND: every action a user triggers from the CLI or UI must be verified server-side. Especially mutation approval and tool installation. The approval UI is not the security gate. The backend is.

2. BROKEN ACCESS CONTROL: keprix is single-user in base form, but multi-user configurations exist. Every API endpoint must verify the caller is authorized to perform that specific action on that specific resource.

3. BUSINESS LOGIC ABUSE: the mutation flow has steps: propose, sandbox, test, approve, install. A request that skips directly to install without approval must be rejected at the backend, regardless of how it arrived.

4. TRUST EXTERNAL SERVICES BLINDLY: AI providers, optional Scout connectors, external tool registries - validate every response. A compromised or misbehaving provider must not be able to cause keprix to install malicious tools.

5. CREDENTIAL EXPOSURE: the vault and redaction layers are the source of truth. Zero credentials in logs, error messages, API responses, or git history. If a user's API key appears in any output, that is a critical bug.

### Mutation safety rules:
- Every mutation runs in a sandboxed environment before approval.
- No tool is installed without explicit user approval.
- Approval is recorded with timestamp and context.
- Irreversible actions (deletes, overwrites, installs) require confirmation gates.
- Audit log every install, every removal, every tool execution that touches the filesystem or network.

---

## 3. API AND ENDPOINT DESIGN (FastAPI)

- Validate all input at the boundary. Pydantic models on every request body and response.
- Never trust query parameters or path variables without validation.
- Return structured errors with a consistent shape: `{error: str, code: str, detail?: str}`.
- Rate limit mutation endpoints. Prevent abuse of the sandbox.
- Health endpoint (`/health`) must be lightweight and not require auth.
- All endpoints that trigger mutations or tool actions must require auth.

---

## 4. TOOL AND MUTATION DESIGN

Every tool keprix generates or installs must inherit these properties:

- Scoped: the tool does exactly what it says, nothing more.
- Reversible: prefer reversible actions. If irreversible, gate with confirmation.
- Auditable: log input, output, and outcome.
- Safe by default: if uncertain, do nothing and report rather than guess and act.
- Human-readable output: no raw stack traces to users. Translate errors into plain language.

When writing prompts for new tools:
- State the tool's scope explicitly.
- State what the tool will NOT do.
- State what happens on failure.
- State what permissions or environment it requires.

---

## 5. FORM AND UI (CLI and future web UI)

CLI output principles:
- One clear action per prompt.
- Confirmation before any destructive or irreversible action.
- Show progress for long-running operations. Never leave the user staring at a blank cursor.
- Errors must state what went wrong, why (if known), and what the user can do next.

If a web UI is built:
- Validate on blur, not on submit and not on every keystroke.
- Once a field is wrong, switch to live validation and clear the error the instant it is fixed.
- Never block paste in any input field.
- Show positive confirmation (green check) not just errors.

---

## 6. TESTING

- All mutations must have sandboxed test coverage before the install path is triggered.
- API endpoints must have integration tests.
- Tool execution paths must have unit tests covering: success, failure, timeout, invalid input.
- Do not mock the mutation sandbox in tests - it is the thing being tested.
- Run tests before any handoff.

---

## 7. BRAND AND NAMING

- keprix is independently branded. It is MIT licensed and open-source.
- Do not write "Carina keprix" anywhere.
- Scout integration is optional and sold separately. Do not add upsell stubs or commercial key prompts in this repo.
- No em dashes, no en dashes, no emojis anywhere.
- Speak like a human: clear, plain, professional. No filler.

---

## 8. COMMIT DISCIPLINE

Build order follows `prompts/` numbering. Commit after each prompt is fully implemented and tested.

Format: `feat: ...` / `fix: ...` / `chore: ...`

Never commit: credentials, `.env` contents, sandbox artifacts, or generated tool binaries.
