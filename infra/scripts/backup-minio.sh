#!/usr/bin/env bash
# MinIO backup script — mc mirror to local backup directory, retain 7 days.
# Usage: bash backup-minio.sh
# Requires: mc (MinIO Client) installed and configured.
# Env vars: MINIO_ALIAS, S3_BUCKET, BACKUP_DIR

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/opt/kb-platform/backups/minio}"
RETENTION_DAYS=7
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
TARGET="${BACKUP_DIR}/${TIMESTAMP}"

MINIO_ALIAS="${MINIO_ALIAS:-local}"
S3_BUCKET="${S3_BUCKET:-kb-assets}"

mkdir -p "${TARGET}"

echo "[$(date)] Starting MinIO backup..."

mc mirror "${MINIO_ALIAS}/${S3_BUCKET}" "${TARGET}/" --overwrite

SIZE=$(du -sh "${TARGET}" | cut -f1)
echo "[$(date)] Backup created: ${TARGET} (${SIZE})"

# Clean up old backups
DELETED=$(find "${BACKUP_DIR}" -maxdepth 1 -mindepth 1 -type d -mtime +${RETENTION_DAYS} -print -exec rm -rf {} \; | wc -l 2>/dev/null || echo "0")
echo "[$(date)] MinIO backup complete."
