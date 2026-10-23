#!/bin/bash
# Build and run Peer Library with Docker Compose.
#
# This replaces the original Amazon-Linux/EC2 bootstrap script, which assumed a
# specific host that this project no longer targets. It is a thin convenience
# wrapper around docker compose; see README.md and SUPABASE_SETUP.md for the
# full production configuration (Supabase PostgreSQL + Storage).
set -euo pipefail

if [ ! -f .env ]; then
    echo "No .env found. Copy .env.example to .env and set SECRET_KEY (and, for"
    echo "production, DATABASE_URL and the SUPABASE_* values) before deploying."
fi

docker compose up -d --build
echo "Peer Library is starting on http://localhost:5000"
echo "Follow logs with: docker compose logs -f web"
