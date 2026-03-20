FROM python:3.12-slim

WORKDIR /app

# Install shared packages
COPY packages/ /packages/
RUN pip install --no-cache-dir \
    -e /packages/shared-config \
    -e /packages/shared-errors \
    -e /packages/shared-models

# Install pipeline worker
COPY services/pipeline-worker/ /app/
RUN pip install --no-cache-dir -e /app/

# Run as non-root user
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
USER appuser

CMD ["celery", "-A", "worker.celery_app:celery_app", "worker", "--loglevel=info", "--concurrency=2", "-Q", "pipeline"]
