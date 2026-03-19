FROM python:3.12-slim

# Install system deps (pg_isready, redis-cli, curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client redis-tools curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install shared packages
COPY packages/ /packages/
RUN pip install --no-cache-dir \
    -e /packages/shared-config \
    -e /packages/shared-errors \
    -e /packages/shared-models \
    -e /packages/shared-schemas

# Install API service
COPY services/api/ /app/
RUN pip install --no-cache-dir -e /app/

# Install Alembic and copy migration files
RUN pip install --no-cache-dir alembic
COPY infra/sql/ /infra/sql/

# Copy entrypoint
COPY infra/docker/api-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8080

ENTRYPOINT ["/entrypoint.sh"]
