#!/usr/bin/env bash
# KB Platform — One-click deployment script
# Usage: bash deploy.sh [--skip-build]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
COMPOSE_BASE="${PROJECT_ROOT}/docker-compose.yml"
COMPOSE_PROD="${PROJECT_ROOT}/infra/docker/docker-compose.production.yml"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[deploy]${NC} $*"; }
warn() { echo -e "${YELLOW}[warn]${NC} $*"; }
fail() { echo -e "${RED}[error]${NC} $*"; exit 1; }

SKIP_BUILD=false
[[ "${1:-}" == "--skip-build" ]] && SKIP_BUILD=true

# --- Pre-flight checks ---
log "Running pre-flight checks..."

# 1. Check .env.production
if [ ! -f "${PROJECT_ROOT}/.env.production" ]; then
    fail ".env.production not found. Copy .env.production.example and fill in secrets."
fi

# 2. Check Docker
command -v docker >/dev/null 2>&1 || fail "Docker not found. Install Docker first."
docker compose version >/dev/null 2>&1 || fail "Docker Compose V2 not found."

# 3. Check compose files exist
[ -f "${COMPOSE_BASE}" ] || fail "docker-compose.yml not found at ${COMPOSE_BASE}"
[ -f "${COMPOSE_PROD}" ] || fail "docker-compose.production.yml not found at ${COMPOSE_PROD}"

# 4. Check SSL certificates
if [ ! -f "${PROJECT_ROOT}/infra/nginx/ssl/fullchain.pem" ]; then
    warn "SSL certificates not found. Generating self-signed for localhost..."
    bash "${PROJECT_ROOT}/infra/nginx/ssl/generate-self-signed.sh" localhost
fi

# 5. Check ports
for PORT in 80 443; do
    if lsof -Pi ":${PORT}" -sTCP:LISTEN -t >/dev/null 2>&1; then
        fail "Port ${PORT} is already in use."
    fi
done

log "Pre-flight checks passed."

# --- Build / Pull ---
if [ "${SKIP_BUILD}" = false ]; then
    log "Building images..."
    docker compose -f "${COMPOSE_BASE}" -f "${COMPOSE_PROD}" \
        --env-file "${PROJECT_ROOT}/.env.production" build
fi

# --- Database migration ---
log "Running database migrations..."
docker compose -f "${COMPOSE_BASE}" -f "${COMPOSE_PROD}" \
    --env-file "${PROJECT_ROOT}/.env.production" \
    run --rm api alembic upgrade head

# --- Start services ---
log "Starting all services..."
docker compose -f "${COMPOSE_BASE}" -f "${COMPOSE_PROD}" \
    --env-file "${PROJECT_ROOT}/.env.production" up -d

# --- Health check ---
log "Waiting for services to become healthy..."
MAX_WAIT=60
ELAPSED=0
while [ $ELAPSED -lt $MAX_WAIT ]; do
    if docker compose -f "${COMPOSE_BASE}" -f "${COMPOSE_PROD}" ps --format json 2>/dev/null | grep -q '"Health":"healthy"'; then
        break
    fi
    sleep 5
    ELAPSED=$((ELAPSED + 5))
    echo -n "."
done
echo ""

if [ $ELAPSED -ge $MAX_WAIT ]; then
    warn "Some services may not be healthy yet. Check with: docker compose ps"
else
    log "All services healthy!"
fi

# --- Output ---
echo ""
log "========================================="
log "  KB Platform deployed successfully!"
log "========================================="
log "  HTTPS:    https://localhost"
log "  API:      https://localhost/api/"
log "  Grafana:  http://localhost:3001 (if monitoring stack is up)"
log ""
log "  Logs:     docker compose -f ${COMPOSE_BASE} -f ${COMPOSE_PROD} logs -f"
log "  Stop:     docker compose -f ${COMPOSE_BASE} -f ${COMPOSE_PROD} down"
log "========================================="
