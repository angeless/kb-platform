FROM python:3.12-slim

# Install system deps (pg_isready, redis-cli, curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client redis-tools curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install shared packages (local, editable)
COPY packages/ /packages/
RUN pip install --no-cache-dir \
    -e /packages/shared-config \
    -e /packages/shared-errors \
    -e /packages/shared-models \
    -e /packages/shared-schemas

# Install locked third-party dependencies
COPY services/api/requirements.lock /app/requirements.lock
RUN pip install --no-cache-dir --no-deps -r /app/requirements.lock

# Install API service (no-deps: all deps already installed above)
COPY services/api/ /app/
RUN pip install --no-cache-dir --no-deps -e /app/

# Install Alembic and copy migration files
RUN pip install --no-cache-dir alembic
COPY infra/sql/ /infra/sql/

# Copy entrypoint
COPY infra/docker/api-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8080

# Run as non-root user
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
USER appuser

ENTRYPOINT ["/entrypoint.sh"]
