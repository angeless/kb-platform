#!/usr/bin/env bash
# Apply v0.51 + v0.53 pending alembic migrations to Aiven Postgres.
#
# RUN FROM A NORMAL TERMINAL (not Claude Code sandbox — sandbox can't resolve
# Aiven external DNS).
#
# Usage:
#   ./scripts/apply_pending_migrations.sh
#   ./scripts/apply_pending_migrations.sh --dry-run    # preview SQL only
#
# Prerequisites:
#   - .env contains valid POSTGRES_* (already verified)
#   - shared_config DSN fix applied (see commit 'fix(shared-config): psycopg2 sslmode')
set -euo pipefail

cd "$(dirname "$0")/.."

# Activate venv
if [[ -d .venv ]]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
else
    echo "ERROR: .venv not found at $(pwd)/.venv" >&2
    exit 1
fi

# Confirm DSN fix is in place
if ! python -c "from shared_config.settings import get_settings; s=get_settings(); assert 'sslmode=' in s.database_url_sync, 'DSN fix not applied'"; then
    echo "ERROR: shared-config DSN fix not in effect (sync URL still has ?ssl=)" >&2
    echo "       Run: pip install -e ./packages/shared-config --force-reinstall --no-deps" >&2
    exit 2
fi

cd infra/sql

if [[ "${1:-}" == "--dry-run" ]]; then
    echo "=== DRY RUN: SQL that would be applied ==="
    alembic upgrade head --sql
    exit 0
fi

echo "=== Current alembic state ==="
alembic current
echo
echo "=== Heads ==="
alembic heads
echo
echo "=== Pending migrations to apply ==="
alembic history -r current:head | head -30
echo
read -p "Apply these migrations to Aiven Postgres? [y/N] " confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "Aborted."
    exit 0
fi

echo "=== Applying ==="
alembic upgrade head

echo
echo "=== New current state ==="
alembic current

echo
echo "✅ Done. Bridge tables (bridge_sync_record, bridge_mapping, bridge_operation) are now live."
