# Prompt 401 / 12: Channel parity matrix

Status: COMPLETED 2026-08-04
Series: Keprix capability mesh  
Depends on: 396 / 07, 397 / 08, 400 / 11  
Blocks: 402  
Writing style: plain ASCII only (no em/en dashes, no emoji).

## Why this exists

Telegram is the flagship, but Discord/Slack/WhatsApp/web_ui should inherit the same core tools by design. Make parity explicit and testable.

## Goal

Publish and check a channel parity matrix: platform x capability node.

## Must-haves

1. Table in docs: platforms vs pilot nodes (`vical`, `calendar`, `contacts`, `companies-house`).
2. Assert `keprix-<platform>` composites still expand `_KEPRIX_CORE_TOOLS` (regression test).
3. Note webhook-safe and admin exceptions.
4. Slash parity: telegram-first OK; other platforms inherit NL tools even if slash lags (document).

## Acceptance

- [ ] Matrix committed.
- [ ] Regression test fails if telegram core tools drop pilot tool names after wiring.
