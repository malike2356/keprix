# Fly fullstack optional recipe
#
# Primary production remains VPS Compose + Caddy:
#   docs/operations/vps-deploy.md
#
# Setup (not one-click):
#   1. fly apps create keprix
#   2. fly postgres create --name keprix-db && fly postgres attach keprix-db -a keprix
#   3. Provision Redis and set KEPRIX_REDIS_URL (Fly Redis or Upstash)
#   4. fly volumes create keprix_data --size 10 --region lhr -a keprix
#   5. fly secrets set KEPRIX_JWT_SECRET=... KEPRIX_SESSION_SECRET=... KEPRIX_VAULT_KEY=... \
#        KEPRIX_ALLOWED_ORIGINS=https://YOUR_APP.fly.dev KEPRIX_INSTANCE_URL=https://YOUR_APP.fly.dev
#   6. fly deploy -c fly.fullstack.toml
#
# Image: docker/Dockerfile.fly (API + Next on one machine)
# Backend-only sketch: fly.backend-only.toml

See also: fly.toml (defaults to the same fullstack settings).
