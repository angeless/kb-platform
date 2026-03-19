#!/bin/bash
set -e

echo "=== KB Platform API Entrypoint ==="

# Step 1: Wait for PostgreSQL
echo "[1/4] Waiting for PostgreSQL..."
until pg_isready -h "${POSTGRES_HOST:-postgres}" -p "${POSTGRES_PORT:-5432}" -U "${POSTGRES_USER:-kb_user}" -q 2>/dev/null; do
    echo "  PostgreSQL not ready, retrying in 2s..."
    sleep 2
done
echo "  PostgreSQL is ready."

# Step 2: Wait for Redis
echo "[2/4] Waiting for Redis..."
until redis-cli -h "${REDIS_HOST:-redis}" -p "${REDIS_PORT:-6379}" ping 2>/dev/null | grep -q PONG; do
    echo "  Redis not ready, retrying in 2s..."
    sleep 2
done
echo "  Redis is ready."

# Step 3: Run Alembic migrations
echo "[3/4] Running database migrations..."
cd /infra/sql
alembic upgrade head
echo "  Migrations complete."

# Step 4: Start API server
echo "[4/4] Starting API server..."
cd /app
exec uvicorn app.main:app --host 0.0.0.0 --port 8080
