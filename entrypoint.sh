#!/bin/sh
# Container entrypoint.
#
# Migrations run here as a single, explicit step BEFORE the web server starts,
# so the multiple Gunicorn workers never race to build the schema. For a
# multi-replica deployment, run migrations as a dedicated one-off job instead
# and set RUN_MIGRATIONS=0 on the web containers.
set -e

export FLASK_APP=app

if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
    echo "[entrypoint] Applying database migrations..."
    flask db upgrade
fi

echo "[entrypoint] Starting: $*"
exec "$@"
