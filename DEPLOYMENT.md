# Deployment and operations

The repository includes a public HTTPS Compose stack in `compose.production.yaml`. It has a Caddy ingress, a private Next.js web service, FastAPI, PostgreSQL/PostGIS, Redis and the maintenance worker. Only ports 80 and 443 are published. Separate edge, application and data networks limit which services can reach each other, and the application containers run as nonroot users. The default `compose.yaml` remains the loopback-only local installation. No public deployment has been performed.

## Before launch

1. Use a Linux server with current Docker Engine and Compose, persistent storage and inbound TCP 80/443 and UDP 443. Point a real DNS name at it. Keep the host patched and restrict administrative access.
2. Copy `.env.production.example` to `.env.production`. Generate three different, random secrets of at least 32 characters. `POSTGRES_PASSWORD` must contain URL-safe characters (`A-Z`, `a-z`, `0-9`, `.`, `_`, `~`, `-`). Set the DNS name and a real certificate contact email. Keep `.env.production` private and out of backups that may be shared.
3. Run `python3 ops/preflight.py .env.production` and `docker compose --env-file .env.production -f compose.production.yaml config --quiet` from the repository root. The example values intentionally fail preflight. Make sure local firewall rules expose only the ingress; the stack does not publish API, database, Redis or web container ports.
4. Before opening registration to the public, the operating organization must approve the service area, retention period, consent/privacy text, emergency escalation process, identity checks, abuse response, backup schedule and restore ownership. Configure policy in the admin UI. Closed-request content retention is disabled until set.

## Start and verify

```sh
docker compose --env-file .env.production -f compose.production.yaml up --build -d
docker compose --env-file .env.production -f compose.production.yaml ps
docker compose --env-file .env.production -f compose.production.yaml exec api python -m app.cli create-admin
curl --fail --silent --show-error https://YOUR_DOMAIN/api/v1/health
```

The API applies Alembic migrations before serving. Wait for all health checks to pass. Caddy obtains and renews HTTPS certificates for the configured public hostname. The browser talks to the same-origin Next.js proxy; Caddy replaces client-supplied `X-Forwarded-For` with the direct peer address, and Next.js signs that address so API rate limits apply per visitor. Keep the web/API network private; otherwise the signed-address trust boundary is weaker. Health at `/api/v1/health` checks database and Redis. Admin health additionally reports the worker's last successful maintenance cycle. Test an actual sign-in and an authorized request lifecycle before inviting users.

## Backups

Back up **both** PostgreSQL and the private evidence volume. The included backup command stops web, API and worker writes, dumps the database, archives the evidence/model volume, records SHA-256 digests, then starts services again. Schedule it during a low-traffic window and send the output to encrypted storage outside the server. The operator must decide backup frequency and retention under the approved policy.

```sh
mkdir -p /private/sahaya-backups
chmod 700 /private/sahaya-backups
python3 ops/backup.py --env-file .env.production --output /private/sahaya-backups
```

Do a restore rehearsal on an isolated host before launch and after schema changes. `python3 ops/restore.py /path/to/backup` checks the manifest, file hashes and archive structure without changing data. `python3 ops/restore.py /path/to/backup --confirm-replace` stops the public services, deletes and recreates the current database, replaces the private volume, then starts services. Use that destructive command only for an approved restore window, and check migration head, health, access controls and a real request's evidence afterward. If a restore fails, the script leaves application services stopped. Keep a separate copy of the production environment configuration and encryption keys in an access-controlled secret store; the backup does not include them.

## Updates and monitoring

- Take a backup before updating. Review migrations and release notes, then run `docker compose --env-file .env.production -f compose.production.yaml up --build -d` and verify health, worker heartbeat and key user flows.
- Monitor `/api/v1/health`, container health, disk use, database growth, backup completion, certificate status, failed login rate and worker freshness. Keep access to logs limited because request metadata may contain sensitive information.
- An unavailable Redis causes mutation requests to fail closed with 503. A failed worker leaves the API available but stops expiry, escalation and retention; the admin health endpoint marks its heartbeat stale.
- The optional speech model can be prepared with `docker compose --env-file .env.production -f compose.production.yaml exec api python -m app.cli prepare-speech`. For optional local LLM suggestions, set `OLLAMA_URL=http://ollama:11434`, start with `--profile ai`, and run `docker compose --env-file .env.production -f compose.production.yaml --profile ai exec ollama ollama pull gemma3:4b`. Its model volume can be redownloaded and is not part of the database/evidence backup. The core request path works without either model. Check OpenStreetMap tile-use requirements or host tiles for significant traffic.

## Release boundary

The software and production configuration can be prepared in this repository, but DNS, server ownership, secrets, real participant verification, legal policy decisions, independent security review, manual assistive-technology review and a measured restore rehearsal require the operator. These are launch gates, not sample data to invent. Sahaya is not emergency dispatch infrastructure.
