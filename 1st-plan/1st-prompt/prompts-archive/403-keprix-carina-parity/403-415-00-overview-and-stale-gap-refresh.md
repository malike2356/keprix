# Prompt 403 / 00: Overview and stale gap refresh

**Status: COMPLETED 2026-08-04** (doc restore + archive refresh 2026-08-07)  
Series: Keprix close Carina parity gaps  
Depends on: none  
Blocks: 404-415  
Writing style: plain ASCII only (no em/en dashes, no emoji).

## Why this exists

The archive doc `archive/keprix-carina-parity-gap-2026-07-30.md` is a snapshot. Agents must not treat every row as still open.

## Goal

1. Annotate the archive doc with a "Status as of 2026-08-04" section mapping each HIGH/CRITICAL Keprix-inbound gap to: OPEN / PARTIAL / DONE / DEFERRED.
2. Point to this programme + the Carina sister programme.
3. Confirm Carina behavioural reference paths under `carina/02-backends/` and `carina/03-frontends/` only (never nested `carina/verlox/`).

## Must-haves

1. Update archive markdown with status map (keep historical tables).
2. Series README progress checkbox for 00.
3. List absolute paths to Carina tenant, governance, and Scout modules used as reference.

## Acceptance

- [x] Archive doc has dated status map.
- [x] Implementing agent can start 01 without re-reading the whole byte comparison.

## What was built

- Status map on `/opt/lampp/htdocs/verlox/archive/keprix-carina-parity-gap-2026-07-30.md` (2026-08-04 filing + 2026-08-07 close).
- Programme + sister programme pointers; Carina reference path table (tenant, GDPR, Scout/Warden, packs).
- Series README progress for 00; restored missing archive doc after workspace offload.
