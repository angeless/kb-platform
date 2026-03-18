FROM python:3.12-slim

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

# Copy env file for defaults
COPY .env.example /app/.env

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
