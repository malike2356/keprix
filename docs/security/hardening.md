# Production hardening

Checklist before exposing Keprix beyond localhost.

## Secrets

- [ ] Replace all `GENERATE_RANDOM_*` placeholders in `.env`
- [ ] Set strong `KEPRIX_ADMIN_PASSWORD` before first boot
- [ ] Rotate `KEPRIX_JWT_SECRET` and `KEPRIX_SESSION_SECRET` on compromise

## Network

- [ ] Bind services to `127.0.0.1` unless behind TLS reverse proxy
- [ ] Restrict Postgres and Redis to internal Docker network in production
- [ ] Set `KEPRIX_ALLOWED_ORIGINS` to your real frontend URL

## Auth

- [ ] Enable `KEPRIX_REQUIRE_2FA` for admin accounts when supported
- [ ] Disable developer mode on shared staging hosts

## Updates

```bash
python3 -m keprix.keprix_cli.main update
python3 -m keprix.keprix_cli.main health
```

## Backups

Schedule [hot backups](../operations/backup.md) before upgrades.
