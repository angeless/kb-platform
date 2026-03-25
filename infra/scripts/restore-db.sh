#!/usr/bin/env bash
# PostgreSQL restore script — restore from gzipped pg_dump backup.
# Usage: bash restore-db.sh <backup_file.sql.gz>
# WARNING: This will DROP and recreate the target database.

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Usage: $0 <backup_file.sql.gz>"
    echo "Available backups:"
    ls -lt "${BACKUP_DIR:-/opt/kb-platform/backups/db}"/kb_db_*.sql.gz 2>/dev/null || echo "  (none found)"
    exit 1
fi

BACKUP_FILE="$1"
POSTGRES_HOST="${POSTGRES_HOST:-postgres}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_DB="${POSTGRES_DB:-kb_platform}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"

if [ ! -f "${BACKUP_FILE}" ]; then
    echo "Error: Backup file not found: ${BACKUP_FILE}"
    exit 1
fi

echo "WARNING: This will DROP and recreate database '${POSTGRES_DB}'."
echo "Backup file: ${BACKUP_FILE}"
read -p "Continue? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

echo "[$(date)] Restoring from ${BACKUP_FILE}..."

# Drop and recreate database
PGPASSWORD="${POSTGRES_PASSWORD}" psql \
    -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d postgres \
    -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='${POSTGRES_DB}' AND pid <> pg_backend_pid();" \
    -c "DROP DATABASE IF EXISTS ${POSTGRES_DB};" \
    -c "CREATE DATABASE ${POSTGRES_DB};"

# Restore
gunzip -c "${BACKUP_FILE}" | PGPASSWORD="${POSTGRES_PASSWORD}" psql \
    -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}"

echo "[$(date)] Restore complete. Run 'alembic upgrade head' to ensure migrations are current."
