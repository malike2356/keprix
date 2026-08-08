# keprix - Prompt 01: Developer Identity and Local Access

## Purpose

keprix has no remote licence server and no commercial key gate. Access control for
a self-hosted install is local:

- **Developer identity** (`keprix init`): full access on this machine, bound to a
  machine fingerprint. No network call.
- **Multi-user auth** (Prompt 08): username/password or SSO for additional users on
  the same instance.

Read `../../../docs/BRAND-BOUNDARY.md`. Do not implement Aiva Keys, Petraclus Keys, or
`keys.petraclus.uk` validation in keprix.

## Output

```text
keprix/backend/keys/developer_identity.py   (exists; extend if needed)
keprix/backend/keys/local_access.py         (new: verify developer mode at runtime)
keprix/backend/keys/routes.py               (optional: status endpoint)
docs/developer-identity.md
tests/keys/test_developer_identity.py
```

## Developer identity flow

1. First run or `keprix init` asks: "Are you the owner of this installation?"
2. On yes: call `create_developer_identity()`.
3. Writes `~/.keprix/identity/` (private key, public key, `dev.json`, audit log).
4. Sets `keprix_DEVELOPER_MODE=true` in `~/.keprix/config.env`.
5. All feature gates treat developer mode as unrestricted on this host.

## Runtime check

`local_access.py`:

```python
def effective_access_level() -> str:
    if verify_developer_identity():
        return "developer"
    return "standard"  # normal authenticated user; no tier gating in keprix v1
```

keprix v1 does not ship paid feature tiers. Every workspace feature is available
to any authenticated user on the instance. Commercial tiers live in Petraclus and
Aiva, not here.

## CLI

```bash
keprix init              # create developer identity
keprix identity status   # show whether developer identity is valid
keprix identity revoke   # remove developer identity
```

## Tests

- `create_developer_identity()` writes files with mode 0600.
- `verify_developer_identity()` returns True on same machine, False after tamper.
- Fingerprint mismatch on copied `dev.json` returns False.
- No HTTP calls during verify (mock `httpx` and assert zero requests).

## Acceptance criteria

- No reference to Aiva Keys, `keys.petraclus.uk`, or upgrade modals in keprix code.
- `PRODUCT_NAME` from constants is "keprix" everywhere in this module.
- Documentation states clearly: commercial products are separate brands.
