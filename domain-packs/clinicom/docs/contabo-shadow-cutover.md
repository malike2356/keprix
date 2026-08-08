# Contabo shadow cutover
Run Keprix only as an out-of-band comparator. Never send its output into the clinical workflow, patient record, or EHR.

1. Keep `CLINICOM_SIDECAR_PROFILE=carina`.
2. Compare capability schemas and approved golden fixtures.
3. Rehearse `switch-sidecar.sh keprix` and immediate `switch-sidecar.sh carina` only in an approved maintenance window.
4. Obtain clinical, security, operations, and owner sign-off.
5. After any Contabo deploy, verify `curl -fsS -o /dev/null -w '%{http_code}\n' https://carinaai.uk/` returns `200`.

Sign-off: owner ___; clinical ___; security ___; operations ___; timestamp ___; rollback owner ___.
