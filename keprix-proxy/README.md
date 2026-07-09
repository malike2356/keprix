# Keprix Credential Proxy

Standalone entry point for the local credential-injection proxy (Prompt 239).

Implementation lives in `src/keprix/proxy/`. Install Keprix, then run:

```bash
keprix proxy setup
keprix proxy start
keprix proxy doctor
```

Or invoke this module directly:

```bash
python -m keprix.proxy.__main__ start
```

See `docs/security/credential-proxy.md`.
