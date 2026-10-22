#!/bin/sh
# Apply migrations, optionally seed demo data, then run the given command.
set -e
echo "running migrations"
alembic upgrade head
if [ "${SEED_DEMO:-false}" = "true" ]; then
  echo "seeding demo data"
  python -m scripts.seed
fi
exec "$@"
