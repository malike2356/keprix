---
name: configure-workspace
description: Conversational durable workspace preferences (timezone, quiet hours, instance URL).
version: 1.0.0
platforms: [linux, macos, windows]
metadata:
  keprix:
    tags: [workspace, preferences, timezone]
    related_skills: [configure-integration, companion-pair]
---

# Configure Workspace

Use when the operator wants to set timezone, language, instance name/URL, or quiet hours.

Call `workspace_config` with `collect` or `configure`. Preferences persist in
`~/.keprix/workspace_settings.json`. Do not send them digging through Settings.
