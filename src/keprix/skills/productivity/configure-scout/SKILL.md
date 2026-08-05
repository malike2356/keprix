---
name: configure-scout
description: Conversational Labyrinth Scout pair and unpair.
version: 1.0.0
platforms: [linux, macos, windows]
metadata:
  keprix:
    tags: [scout, governance, configuration]
    related_skills: [configure-provider, configure-channel]
---

# Configure Scout

Use when the operator wants to pair Scout, connect governance, or unpair monitoring.

## Flow

1. `scout_config` action `collect` (or `requirements`).
2. Ask for Scout endpoint, then API key (one at a time). Never echo the key.
3. On unpair: confirm local-only responsibility, then `remove` with `accept_responsibility=true`.
4. Forbidden: send them only to a buried Settings page.
