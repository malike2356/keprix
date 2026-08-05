# Prompt 400 / 11: Rollup pack (playbooks, skills, cron)

Status: COMPLETED 2026-08-04
Series: Keprix capability mesh  
Depends on: 393 / 04, 396 / 07  
Blocks: 401, 402  
Writing style: plain ASCII only (no em/en dashes, no emoji).

## Why this exists

Automation is how the mesh runs unattended. Skills and cron must compose pilot tools and stay channel-notifiable.

## Goal

Expose / document playbook+cron composition for mesh tools; promote one pilot skill to a cron-friendly reminder or follow-up.

## Baseline

| Piece | Path |
|---|---|
| Skills | `src/keprix/skills/` |
| Agent OS promote | `agent_os/templates/` |
| Cron | `cron/` |

## Must-haves

1. Graph nodes for `playbooks`, `cron`, `skills` with honest status.
2. One end-to-end template: skill that books or lists slots then optional `send_message`.
3. Agent OS or docs path to promote that skill to cron (reuse existing promote helpers).
4. Tests for template rendering or dry-run promote.

## Acceptance

- [ ] Documented path from chat skill -> cron job delivering to Telegram home.
- [ ] No parallel scheduler invented.
