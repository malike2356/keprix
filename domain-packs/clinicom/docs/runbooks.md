# Runbooks
## Provider outage
Keep the profile unchanged, label stub results, disable affected capability badges, and use Carina only after owner-approved switch procedure.
## Leakage or suspected cross-organisation access
Stop connector traffic, revoke bootstrap credentials, preserve audit metadata, and investigate without copying patient content into logs.
## Bad model output or mistranslation
Stop acceptance, retain the original human-visible encounter in Clinicom, mark the output rejected, and replay the golden fixture.
## Latency
Apply bounded retries only to idempotent calls. Degrade to labelled continuity mode rather than blocking human communication.
## Rollback
Use `switch-sidecar.sh carina` only after approved incident response. Verify Clinicom health and `https://carinaai.uk/` HTTP 200 after any Contabo deploy.
