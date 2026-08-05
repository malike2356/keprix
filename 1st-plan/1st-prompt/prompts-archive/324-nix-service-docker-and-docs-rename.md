# Keprix Prompt 324: Nix Service Docker and Docs Rename

## Purpose

Complete the platform-level rename for Nix, Docker, service units, docs, and install assets.

## Preconditions

Complete Prompts 322 and 323 first.

## Tasks

1. Rename Nix service wording from Hermes to Keprix where it is first-party.
2. Preserve compatibility where existing users may already have:
   - `services.hermes-agent`
   - `HERMES_HOME`
   - `.hermes`
   - container names or state directories
3. Add new preferred Nix names:
   - `services.keprix`
   - `KEPRIX_HOME`
   - `.keprix`
4. Update Docker docs and container labels to Keprix.
5. Update installation docs.
6. Update generated CLI reference docs.
7. Add migration docs:
   - old Nix service name to new service name
   - old state directory to new state directory
   - old env vars to new env vars

## Acceptance criteria

- New docs use Keprix names.
- Old Nix names remain documented as compatibility only.
- No user loses existing state because of rename.
- Service migration is explicit and reversible.

## Verification

```bash
python -m pytest tests/cli tests/config -q
python3 scripts/fix-writing-style.py
rg -n "Hermes|hermes|HERMES|\\.hermes|hermes-agent" docs src/keprix/nix docker pyproject.toml
```

Every remaining match must be compatibility, legal attribution, or upstream reference.
