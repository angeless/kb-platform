FROM python:3.12-slim

WORKDIR /app

# Install shared packages (local, editable)
COPY packages/ /packages/
RUN pip install --no-cache-dir \
    -e /packages/shared-config \
    -e /packages/shared-errors \
    -e /packages/shared-models

# Install locked third-party dependencies
COPY services/ai-orchestrator/requirements.lock /app/requirements.lock
RUN pip install --no-cache-dir --no-deps -r /app/requirements.lock

# Install AI orchestrator (no-deps: all deps already installed above)
COPY services/ai-orchestrator/ /app/
RUN pip install --no-cache-dir --no-deps -e /app/

# Copy env file for defaults
COPY .env.example /app/.env

# Run as non-root user
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
USER appuser

CMD ["celery", "-A", "orchestrator.celery_app:celery_app", "worker", "--loglevel=info", "--concurrency=2"]
