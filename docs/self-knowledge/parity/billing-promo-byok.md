# Billing promo and BYOK

Promo codes redeem against existing catalog price ids only (no new Stripe Prices).
POST /api/billing/portal/checkout accepts promo_code; trial_days can be raised by promo.
BYOK keys stored with AES-GCM (KEPRIX_BYOK_MASTER). Public APIs return hint only.
