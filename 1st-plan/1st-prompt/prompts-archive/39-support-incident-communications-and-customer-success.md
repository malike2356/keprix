# keprix - Prompt 39: Support, Incident Communications, And Customer Success

## Purpose

Add support and incident communication workflows so keprix can help users, report problems, publish incident notes, and guide customers through setup, billing, product usage, and recovery.

For self-host users, support may be local and community-driven. For managed Aiva customers, support can be commercial. keprix should provide the product foundation without bundling paid support promises.

## Scope

Implement:

- Support chat workspace.
- Help request intake.
- Local diagnostics bundle.
- Support ticket export.
- Incident log.
- Public incident post generator.
- Newsletter or release note templates.
- Customer success checklist.
- Onboarding progress.
- Setup rescue workflow.
- Human handoff hooks.
- Community support links.

## Output Paths

```text
keprix/backend/support/
  __init__.py
  tickets.py
  diagnostics.py
  incidents.py
  articles.py
  onboarding.py
  handoff.py
  schemas.py

keprix/ui/web/support/
keprix/docs/support/
keprix/tests/support/
```

## Support Workflows

Support must handle:

- Installation issue.
- Provider setup issue.
- Telegram or channel issue.
- Billing issue where commerce is enabled.
- Data import issue.
- Failed job.
- Security warning.
- Lost admin access.
- Backup and restore.
- Bug report.
- Feature request.

## Diagnostics Bundle

Generate a safe diagnostics bundle:

- Version.
- OS.
- Enabled modules.
- Health checks.
- Recent redacted errors.
- Job failures.
- Provider status without secrets.
- Disk usage.
- Config summary without secrets.

Never include plaintext secrets, customer data, private messages, or raw credentials.

## Tests

Add tests for:

- Diagnostics bundle redacts secrets.
- Support ticket can be exported.
- Incident post can be generated.
- Onboarding checklist updates.
- Human handoff respects privacy settings.

## Acceptance Criteria

- keprix can guide users through common problems.
- Support diagnostics are safe to share.
- Incident communication is structured.
- Customer success workflows exist without promising paid support in the free product.
