# KB Platform — Upgrade Guide

## Steps

### 1. Backup (required)
Run backup-db.sh and backup-minio.sh before any upgrade.

### 2. Pull new code
git fetch origin && git checkout v{new}

### 3. Check CHANGELOG
- New migrations?
- New config items?
- Breaking changes?

### 4. Update config
Compare .env.production with .env.production.example for new items.

### 5. Execute upgrade
Build -> stop -> migrate -> start:
docker compose build
docker compose down
docker compose run --rm api alembic upgrade head
docker compose up -d

### 6. Verify
curl -k https://localhost/api/_version
curl -k https://localhost/api/health/ready

### 7. Rollback (if needed)
Stop -> restore code -> restore DB -> restart

## Rules
- No backup, no upgrade
- Check Breaking Changes
- Migrate failures: restore first, debug later
- Upgrade during low-traffic hours
