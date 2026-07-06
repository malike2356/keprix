# Skills and plugins

Skills are packaged capability bundles that extend what Keprix can do beyond its built-in tool set. A skill can add new tools, new slash commands, new UI panels, or new data connectors. Skills are distributed as signed packs and installed from the Hub or directly via the API.

## Skills vs tools vs packs

| Concept | What it is |
| --- | --- |
| **Tool** | A single Python-callable function the agent can invoke (see [Built-in tools](tools.md)) |
| **Skill** | A bundle of related tools, a manifest, and optional UI components |
| **Pack** | A distributable archive (`.kxpack`) containing one or more skills |
| **Domain pack** | A pack scoped to an industry vertical (e.g. legal, healthcare, security) |

## Hub (`/hub`)

The Hub is the in-app catalogue for discovering and installing skills and packs.

- Browse available packs by category
- View pack manifest: included tools, declared network hosts, required env vars
- Install or uninstall packs with one click
- Rate and review community packs

The Hub also shows installed packs with version and update status.

## Browsing installed skills

```bash
python3 -m keprix.keprix_cli.main skills
```

Lists all registered skills with their tool count and enabled status.

## Installing a pack

### From the Hub UI

1. Open **Workspace > Skills** or **Workspace > Hub** (`/hub`).
2. Find the pack you want.
3. Review its manifest, especially `network_hosts` (any external URLs the tools will call).
4. Click **Install**. Domain packs with elevated permissions prompt for admin approval.

### Via API

```http
POST /api/hub/install
Content-Type: application/json

{
  "pack_id": "keprix-security-osint",
  "version": "1.2.0"
}
```

### From a local file

```bash
python3 -m keprix.keprix_cli.main packs install /path/to/pack.kxpack
```

## Writing a skill pack

A pack is a directory with this structure:

```
my-skill/
  manifest.json        # Pack metadata
  tools/
    search_cve.py      # Individual tool files
    scan_port.py
  ui/
    panel.tsx          # Optional: workspace sidebar panel (React)
  README.md
```

**manifest.json** minimum:

```json
{
  "id": "my-skill",
  "name": "My Skill",
  "version": "1.0.0",
  "description": "Does X and Y",
  "tools": ["tools/search_cve.py", "tools/scan_port.py"],
  "network_hosts": ["nvd.nist.gov"],
  "required_env": ["NVD_API_KEY"],
  "license": "MIT"
}
```

Pack the directory:

```bash
python3 -m keprix.keprix_cli.main packs pack ./my-skill --out my-skill-1.0.0.kxpack
```

See [Skill packs](../community/packs.md) for contribution guidelines and signing requirements.

## Disabling skills per session

Pass `--skills` with an exclusion list at the CLI:

```bash
python3 -m keprix.keprix_cli.main chat --skills -osint,-security
```

Or in the web UI chat settings, toggle individual skills under **Active tools**.

## Pack gate

The pack gate lets administrators restrict which packs can be installed on the instance, require approval workflows for elevated packs, and enforce version pinning. Configure at **Settings > Pack gate** (`/settings/pack-gate`).

```bash
KEPRIX_PACK_GATE_ENABLED=true
KEPRIX_PACK_GATE_REQUIRE_ADMIN_APPROVAL=true
KEPRIX_PACK_GATE_BLOCKLIST=keprix-experimental-*
```

## API

| Action | Method | Endpoint |
| --- | --- | --- |
| List installed skills | GET | `/api/skills` |
| List hub catalogue | GET | `/api/hub/catalogue` |
| Install pack | POST | `/api/hub/install` |
| Uninstall pack | DELETE | `/api/hub/packs/{id}` |
| Pack gate config | GET/PUT | `/api/settings/pack-gate` |

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Pack install rejected | Pack gate enabled, approval pending | Admin must approve in Settings > Pack gate |
| Skill tools missing from agent | Skill disabled or pack not loaded | Check `python3 -m keprix.keprix_cli.main skills` output |
| Required env var warning | Pack needs a key not in `.env` | Add the variable, restart backend |
| Pack signature invalid | Pack file corrupted or unsigned | Re-download; only install signed packs from trusted sources |

## Related

- [Built-in tools](tools.md)
- [Hub and domain packs](hub-and-packs.md)
- [Skill packs community guide](../community/packs.md)
- [Agent runtime](agent.md)
