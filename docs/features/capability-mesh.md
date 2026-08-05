# Capability mesh (Keprix)

Status: programme 389-402 **COMPLETED** 2026-08-04. Spine for linking workspace features, Keprix AI, and channels (especially Telegram).

## Problem

Nav/UI breadth exceeds agent/channel reach. Cross-module links are informal. Without a mesh, each feature stays an island.

## Architecture (four layers)

1. **Capability spine:** `tools.registry` + `_KEPRIX_CORE_TOOLS` / `keprix-<platform>` (including `keprix-telegram`).
2. **Object mesh:** durable shared IDs (`contact_id`, `workspace_event_id`, `vical_booking_id`, company numbers, …) via `keprix.capability_mesh.ids`.
3. **Capability graph:** feature nodes + edges. Package: `src/keprix/capability_mesh/`.
4. **Procedural overlay:** skills compose tools (`agent_os/templates/mesh_book_and_notify.skill.md`); cron/`send_message` for outbound.

Channel Shield is ingress safety only. Do not invent a second universal API bus.

## Companies House path (tool exposure recipe)

1. Domain service + tests.
2. `registry.register(...)` with `check_fn`.
3. Named toolset + `_KEPRIX_CORE_TOOLS` when channel-default.
4. Graph node `tools` / `channel_surfaces` / `status: wired`.
5. Update `agent-surface-access.md`.
6. Smoke via pytest / staged Telegram.

## Pilot vertical (shipped)

| Surface | Tools / UX |
| --- | --- |
| Agent / Telegram | `vical_offer_slots`, `vical_create_booking`, `vical_list_bookings`, `vical_cancel_booking`, `calendar_list_events`, `contacts_search`, `contacts_get` |
| Slash | `/slots`, `/bookings` (product slash executor) |
| UI | `/vical` Related links (calendar/contact/public book) |
| IDs | booking.contact_id; calendar event.metadata.vical_booking_id |
| Reminders | `KEPRIX_VICAL_CHANNEL_REMINDERS=1` + `KEPRIX_VICAL_REMINDER_TARGET` |

## Graph / DoD / audit

```bash
cd keprix
bash scripts/check-capability-mesh.sh
PYTHONPATH=src python3 -m keprix.capability_mesh discovery --write
PYTHONPATH=src pytest tests/capability_mesh tests/vical -q
```

Soft DoD: only `status=wired` + telegram must list tools present in core/`keprix-telegram`.

Gap report: `docs/architecture/capability-mesh-gap-report.md`.

## Channel parity

`keprix-telegram`, `keprix-discord`, `keprix-slack`, `keprix-whatsapp`, and `keprix-cli` all expand `_KEPRIX_CORE_TOOLS`, so pilot tools inherit across platforms. Slash UX is Telegram-first; other platforms use NL tool calls.

## Feature flags

| Env | Purpose | Default |
| --- | --- | --- |
| `KEPRIX_VICAL_ENABLED` | viCal tools/ECHO | `1` |
| `KEPRIX_VICAL_CHANNEL_REMINDERS` | send_message on reminder windows | `0` |
| `KEPRIX_VICAL_REMINDER_TARGET` | Channel target for reminders | unset |
| `KEPRIX_MESH_USER_ID` | Default user for mesh tools | `default` |

## Related

- `docs/features/agent-surface-access.md`
- Archived prompts: `1st-plan/1st-prompt/prompts-archive/389-402-*.md`
- Build order: `ref-389-keprix-capability-mesh-build-order.md`
