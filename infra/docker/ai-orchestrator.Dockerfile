FROM python:3.12-slim

WORKDIR /app

# Install shared packages
COPY packages/ /packages/
RUN pip install --no-cache-dir \
    -e /packages/shared-config \
    -e /packages/shared-errors \
    -e /packages/shared-models

# Install AI orchestrator
COPY services/ai-orchestrator/ /app/
RUN pip install --no-cache-dir -e /app/

# Copy env file for defaults
COPY .env.example /app/.env

CMD ["celery", "-A", "orchestrator.celery_app:celery_app", "worker", "--loglevel=info", "--concurrency=2"]
