# Release signing

Stub for verifying Keprix release artifacts.

- PyPI publish workflow can attach Sigstore attestations to built distributions (`sigstore` / `*.sigstore.json` on tagged publishes).
- Prefer a git checkout or pinned release ref over piping installers from the network. Production VPS path: [VPS deploy](../operations/vps-deploy.md).
- `scripts/install-curl.sh` is a thin remote entrypoint; treat raw `curl | bash` as unsafe for production. Prefer cloning a tagged ref or using `scripts/bootstrap-do-droplet.sh` / Compose deploy scripts.
- `scripts/install-verified.sh` is reserved for checksum/Sigstore verification flows when populated.

## Related

- [Cloud deploy](../getting-started/cloud-deploy.md)
- [Install](../getting-started/install.md)
- [Hardening](hardening.md)
