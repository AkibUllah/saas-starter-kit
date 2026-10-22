#!/usr/bin/env bash
# Codespaces start hook: dev compose stack (Postgres, Redis, API with reload, Next.js dev server).
# The backend entrypoint runs `alembic upgrade head` and, with SEED_DEMO=true, the seed script.
set -euo pipefail
cd "$(dirname "$0")/.."

[ -f .env ] || cp .env.example .env

docker compose up -d --build

echo "waiting for the API on :8000 ..."
for _ in $(seq 1 90); do
  if curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

# Idempotent: makes sure migrations and demo data are in place and prints the credentials.
docker compose exec -T backend alembic upgrade head
docker compose exec -T backend python -m scripts.seed

echo "waiting for the Next.js dev server on :3000 (first start runs npm ci in the container) ..."
for _ in $(seq 1 120); do
  if curl -fsS -o /dev/null http://127.0.0.1:3000/ 2>/dev/null; then
    break
  fi
  sleep 3
done

cat <<'MSG'

SaaS Starter Kit is up.
  App:       forwarded port 3000          demo@saaskit.dev / Demo1234!  (owner of Acme Dhaka)
                                          admin@saaskit.dev / Admin1234! (platform admin, /admin)
  API docs:  forwarded port 8000, path /api/v1/docs
  Emails:    verification / invite / reset links are printed by: docker compose logs backend
MSG
