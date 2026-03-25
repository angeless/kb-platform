#!/usr/bin/env bash
# Generate self-signed SSL certificates for development/internal use.
# Usage: bash generate-self-signed.sh [domain]
# Output: fullchain.pem + privkey.pem in the current directory.

set -euo pipefail

DOMAIN="${1:-localhost}"
DAYS=365
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Generating self-signed certificate for: ${DOMAIN}"

openssl req -x509 -nodes -days "${DAYS}" \
    -newkey rsa:2048 \
    -keyout "${SCRIPT_DIR}/privkey.pem" \
    -out "${SCRIPT_DIR}/fullchain.pem" \
    -subj "/CN=${DOMAIN}" \
    -addext "subjectAltName=DNS:${DOMAIN},DNS:*.${DOMAIN},IP:127.0.0.1"

echo "Certificates generated:"
echo "  ${SCRIPT_DIR}/fullchain.pem"
echo "  ${SCRIPT_DIR}/privkey.pem"
echo ""
echo "For production, use Let's Encrypt instead (see docker-compose.production.yml certbot service)."
