# Cloud deploy

Deploy Keprix on a VPS with Docker Compose. Cloud bootstrap scripts (`bootstrap-aws-ec2.sh`, `bootstrap-do-droplet.sh`) are planned in Prompt 33.

## Common pattern

1. Provision Ubuntu 24.04 with at least 4 GB RAM and 40 GB disk
2. Install Docker and Compose
3. Clone the repository and copy `.env`
4. Set `BACKEND_BIND=0.0.0.0` and `FRONTEND_BIND=0.0.0.0` only behind a reverse proxy
5. Run `docker compose -f docker/docker-compose.yml up -d --build`
6. Terminate TLS at nginx or Caddy; proxy `/` to port 3000 and `/api` to 3333

## AWS EC2

- Use a `t3.medium` or larger in your region
- Open ports 80 and 443 on the security group only
- Attach an elastic IP for stable DNS
- Store secrets in SSM Parameter Store; inject into `.env` at boot

## DigitalOcean

- Droplet with Docker marketplace image
- Enable backups on the droplet volume
- Use a managed database only if you split Postgres out of Compose

## Post-deploy

Complete [First run](first-run.md), then review [Hardening](../security/hardening.md).
