# Telegram cutover: one bot, Keprix gateway home

Local cutover so Telegram uses Keprix gateway with Hermes command/skill parity
plus Keprix product modules. Use this machine's local Hermes and Keprix homes;
do not rely on Contabo for this path.

## Goal

- Keep Keprix **gateway Telegram** as the command/skill UX (not Channel Shield alone).
- Hermes-class `/help`, command menu, and skill slash surface from `~/.keprix/skills`.
- Keprix-only commands (`/playbook`, `/research`, `/crew`, …) in the same help/menu.
- One Telegram bot token pointed at Keprix gateway; retire Hermes gateway for that chat.

## Preconditions

1. Local Hermes install present (`hermes --version`, typically pipx 0.17.x).
2. Local Keprix tree at `/opt/lampp/htdocs/verlox/keprix` with `~/.keprix`.
3. Skills synced (bundled + optional):

```bash
cd /opt/lampp/htdocs/verlox/keprix
export PYTHONPATH=src
python3 -c "from keprix.tools.skills_sync import sync_skills, restore_official_optional_skill; print(sync_skills(quiet=False)); print(restore_official_optional_skill('all', restore=True))"
```

4. Parity gate green:

```bash
bash scripts/check-telegram-gateway-parity.sh
```

## Cutover steps

1. **Stop Hermes gateway** for the shared bot (only one process may own a Telegram token):

```bash
# If Hermes runs as a user service or foreground process, stop it first.
hermes gateway stop 2>/dev/null || true
# Or stop whatever systemd/user unit owns the Hermes gateway locally.
```

2. **Point the Telegram token at Keprix**. Prefer a single source of truth in
   `~/.keprix/.env` (or the profile env Keprix loads). Copy the bot token from
   the Hermes env only if this is the intentional shared bot. Do not commit
   tokens. Do not paste tokens into chat logs.

3. **Start Keprix gateway**:

```bash
cd /opt/lampp/htdocs/verlox/keprix
# Use your normal local start path, for example:
keprix gateway start
# or: python -m keprix_cli gateway start
```

4. **Refresh Telegram menus** by restarting the gateway after skills sync so
   `set_my_commands` rebuilds from `telegram_menu_commands()` (core + product +
   skills up to the Bot API cap).

5. **Smoke in Telegram** (same chat that previously talked to Hermes):

- `/help` and `/commands` show Hermes-class session commands plus Keprix Product.
- `/billing` returns Keprix product billing (not only Nous).
- `/credits` still covers Nous terminal credits when logged in.
- `/playbook`, `/research`, `/crew` respond via product slash (not "unknown").
- A skill slash from the synced tree (for example a bundled skill shown in
  `/commands`) loads and runs.

6. **Leave Hermes gateway stopped** for that bot. Hermes CLI/TUI can remain
   installed for reference; only the Telegram ownership moves.

## Rollback

1. Stop Keprix gateway.
2. Restore the token to Hermes env if you moved it.
3. Start Hermes gateway again.
4. Confirm `/help` on Hermes.

## Surpass notes

Hermes still leads on maturity (polish, battle-tested edge cases). Keprix should
lead on:

- Skill depth after optional sync (bundled + official optional under `~/.keprix/skills`).
- Product modules on the same Telegram surface (playbook, research, crew, data,
  ML, governance, billing product portal).
- Verlox/Carina-adjacent product features that Hermes does not ship.

## Related

- `scripts/check-telegram-gateway-parity.sh`
- `docs/architecture/hermes-agent-parity-inventory.md`
- `src/keprix/gateway/slash/product.py`
