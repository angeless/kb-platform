#!/usr/bin/env bash
# PostgreSQL backup script — pg_dump + gzip, retain last 7 days.
# Usage: bash backup-db.sh
# Env vars: POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD, BACKUP_DIR

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/opt/kb-platform/backups/db}"
RETENTION_DAYS=7
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
FILENAME="kb_db_${TIMESTAMP}.sql.gz"

POSTGRES_HOST="${POSTGRES_HOST:-postgres}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_DB="${POSTGRES_DB:-kb_platform}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"

mkdir -p "${BACKUP_DIR}"

echo "[$(date)] Starting database backup..."

PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump \
    -h "${POSTGRES_HOST}" \
    -p "${POSTGRES_PORT}" \
    -U "${POSTGRES_USER}" \
    -d "${POSTGRES_DB}" \
    --no-owner \
    --no-privileges \
    | gzip > "${BACKUP_DIR}/${FILENAME}"

SIZE=$(du -sh "${BACKUP_DIR}/${FILENAME}" | cut -f1)
echo "[$(date)] Backup created: ${FILENAME} (${SIZE})"

# Clean up old backups
DELETED=$(find "${BACKUP_DIR}" -name "kb_db_*.sql.gz" -mtime +${RETENTION_DAYS} -print -delete | wc -l)
if [ "${DELETED}" -gt 0 ]; then
    echo "[$(date)] Cleaned ${DELETED} backup(s) older than ${RETENTION_DAYS} days"
fi

echo "[$(date)] Database backup complete."
