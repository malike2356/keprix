---
name: companion-pair
description: Pair a companion phone or desktop device via short code and QR.
version: 1.0.0
platforms: [linux, macos, windows]
metadata:
  keprix:
    tags: [companion, mobile, pairing]
    related_skills: [configure-workspace]
---

# Companion Pair

Use when the operator says pair my phone, companion app, or mobile device.

1. Call `companion_config` action `create`.
2. Show the short `code` and expiry; mention QR if the client can render it.
3. The device confirms in-app (or via `confirm` with pairing_id + code + device_name).
4. Never speak API tokens aloud.
5. `list` / `remove` for device management.
