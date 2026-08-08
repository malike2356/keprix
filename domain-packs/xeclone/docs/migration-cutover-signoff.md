# Migration cutover and sign-off

## Honest Phase 1 status

Carina remains the live path for inbound webhooks and OAuth in Phase 1.
This Keprix sidecar is ready for **local/staging pilot only**.

## Autonomous mode

**OFF** unless separately signed by the owner. This pack does not enable
autonomous engagement.

## Wave gates (summary)

1. Shadow draft comparison (no publish)
2. Keprix draft with Carina/product approval UI
3. Inbound migration (future)
4. Vault/token migration (future)
5. Media jobs (stubs now)
6. Autonomous mode (separate sign-off only)

Each gate needs traffic percentage, observation period, metrics, stop limits,
fallback owner and documented rollback.

## Archive rule

Archive prompts only after owner consent/sign-off and production profile is
documented honestly. Do not claim Contabo/production cutover from this pack alone.
