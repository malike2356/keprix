# Four C's Audit

Use this skill when the operator asks for `/four-cs-audit`, OS maturity scoring, or an AI operating system readiness check.

## Process

1. Identify the workspace or vault path.
2. Run the maturity audit API or `keprix agent-os maturity run`.
3. Present the total score and four dimensions: Context, Connections, Capabilities, Cadence.
4. Rank gaps by leverage.
5. Offer to export the audit to the level-up remediation flow.

## Heuristics

- Context: `context/about-business.md`, `about-me.md`, `priorities.md`, writing samples or onboard intake.
- Connections: tier-1 domains in `connections.md` with `status: live`.
- Capabilities: skills, promoted automations, headless actions.
- Cadence: cron jobs, recent run ledger entries, weekly audit cadence.

Do not inflate scores when files are missing. Low scores should include concrete next actions.
