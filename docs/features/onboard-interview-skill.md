# Onboard Interview Skill

The onboard interview is a seven-question day-one setup flow for Agent OS.

It writes:

- `context/about-business.md`
- `context/writing-samples.md`
- `context/priorities.md`
- `context/about-me.md`
- `context/guardrails.md`
- `context/cadence-preferences.md`
- `context/intake.json`
- `connections.md`

The generated `context/intake.json` is machine-readable input for the Four C's maturity audit.

## API

- `POST /api/agent-os/onboard/start`
- `POST /api/agent-os/onboard/{id}/answer`
- `POST /api/agent-os/onboard/{id}/complete`
- `GET /api/agent-os/onboard/{id}`

Completing the flow records the `onboard.completed` Agent OS onboarding event.
