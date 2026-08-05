# Conditional workflows

Condition ops: `eq`, `ne`, `present`, `in`.

Shipping template: `vical_confirmed_create_lead` (booking confirmed -> create_lead / link booking).

Dry-run helper: `keprix.workflows.conditions.dry_run_booking_confirmed`.

Mesh: leads node links to vical via `vical_booking_id`.
