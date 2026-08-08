# Air-gap / offline Universal Sidecar

## Bundle contents (operator-assembled)

- Signed Python wheels or container image for Keprix + Universal Sidecar
- Pinned domain packs with checksums
- JSON Schema and example manifests
- Offline docs (`docs/universal-sidecar/`)
- Optional local model weights if the deployment requires them

## Rules

- **No telemetry**: disable phone-home, update checks, and crash upload.
- Verify signatures and checksums before install.
- Prefer `environment: airgap` in `keprix.sidecar.yaml`.
- Egress allowlist empty except intentional loopback / private product API.
- Upgrades are operator-driven expand/migrate/contract; no auto-enable of new
  risky capabilities.

## Install sketch

```bash
# On a connected build host
pip download keprix -d ./wheels
# Transfer wheels/ to air-gapped host
pip install --no-index --find-links=./wheels keprix
python -m keprix.universal_sidecar.app
```
