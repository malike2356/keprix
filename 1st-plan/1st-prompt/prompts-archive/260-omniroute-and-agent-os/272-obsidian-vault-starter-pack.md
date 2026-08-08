# Keprix - Prompt 272: Obsidian vault starter pack

**Series:** Chase five tools adoption **267-272**.  
**Master reference:** `../prompts-archive/ref-266-chase-five-tools-adoption-master-reference.md`  
**Working directory:** `/opt/lampp/htdocs/verlox/keprix/`

---

## 1. What this prompt builds

**Obsidian vault starter Hub pack**: conventions, folder template, and `KEPRIX.md` bootstrap for operators using Obsidian alongside Keprix (Chase bonus Obsidian skills pattern + **259** vault provider).

Pack installs into operator vault path:

```
vault/
  KEPRIX.md                 # session bootstrap for agents
  00-inbox/
  01-projects/
  02-areas/
  03-resources/
  04-archive/
  templates/
    daily-note.md
    meeting.md
    research-summary.md
  .keprix/
    vault-manifest.json
```

**Non-goals:**

- Obsidian desktop plugin in Keprix core
- Mandatory Obsidian for all users
- Sync service (operator uses Obsidian Sync / git)

---

## 2. Already built (do not reimplement)

| Area | Location |
| --- | --- |
| Obsidian export | existing export flows if any |
| llm-wiki skill | vault-friendly markdown patterns |
| Vault provider (planned) | **259** universal vault provider |
| Agentic OS memory map | **258** structured workspace |

---

## 3. Architecture

```text
Hub card: obsidian-vault-starter
        |
        v
keprix vault init --pack obsidian-starter --path ~/vault
        |
        v
Copies pack files + writes manifest
        |
        v
259 vault provider reads .keprix/vault-manifest.json
        |
        v
Agent loads KEPRIX.md via vault tools / llm-wiki
```

---

## 4. Vault manifest

```json
{
  "pack": "obsidian-vault-starter",
  "version": "1.0.0",
  "keprix_session_root": "KEPRIX.md",
  "folders": {
    "inbox": "00-inbox",
    "projects": "01-projects",
    "areas": "02-areas",
    "resources": "03-resources",
    "archive": "04-archive"
  },
  "templates": ["daily-note", "meeting", "research-summary"]
}
```

---

## 5. Hub pack contents

**optional-skills/productivity/obsidian-vault-starter/**

| File | Purpose |
| --- | --- |
| `SKILL.md` | When to use vault; link to `llm-wiki` |
| `pack/` | Folder tree + templates |
| `scripts/init_vault.py` | Copy pack to target path |

**KEPRIX.md** sections:

- Active projects (wikilinks)
- Standing instructions for agents
- Links to `00-inbox` processing rules
- Integration with Keprix session export path

---

## 6. API / CLI

```bash
keprix vault list-packs
keprix vault init --pack obsidian-starter --path /path/to/vault
keprix vault validate --path /path/to/vault
```

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/vault/packs` | List available packs |
| POST | `/api/vault/init` | `{ pack, path }` server-side path only if allowed |

For desktop/local installs, CLI is primary; API optional for remote workspace roots.

---

## 7. UI

`/vault/setup` wizard (or Agent OS onboarding **265** step):

- Pick pack: Obsidian starter
- Choose vault path
- Validate manifest
- Open `KEPRIX.md` in editor link

Hub card with install count and docs link.

---

## 8. Files to create

```
src/keprix/vault/
  pack_registry.py
  vault_init_service.py
  vault_validator.py

src/keprix/optional-skills/productivity/obsidian-vault-starter/
  SKILL.md
  pack/...
  scripts/init_vault.py

src/keprix/api/
  vault_pack_routes.py

frontend/src/app/(workspace)/vault/setup/page.tsx

docs/features/obsidian-vault-starter-pack.md

tests/vault/
  test_vault_init_service.py
  test_vault_validator.py
```

---

## 9. Acceptance criteria

- `keprix vault init` copies full tree; `vault-manifest.json` valid.
- `keprix vault validate` passes on initialized vault; fails on empty dir with clear error.
- `KEPRIX.md` contains agent instructions and folder map.
- Templates render with `{{date}}` placeholder replaced on use (document substitution).
- Hub lists pack; skill install does not duplicate core files incorrectly.
- **259** stub interface documented: `VaultProvider.resolve_path()` reads manifest folders.

---

## 10. Dependencies

- **Soft:** **259** universal vault provider (init works standalone)
- **Related:** **258** workspace memory map
- **Last in pack:** ship after **267-271** or in parallel if **259** stub exists
