FROM node:20-slim AS builder

WORKDIR /app

# Install dependencies
COPY apps/web/package.json apps/web/package-lock.json* ./
RUN npm ci --ignore-scripts

# Copy source and build
COPY apps/web/ ./
RUN npm run build

# --- Production stage ---
FROM node:20-slim

WORKDIR /app

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

# Run as non-root user
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
USER appuser

EXPOSE 3000

ENV PORT=3000 HOSTNAME="0.0.0.0"
CMD ["node", "server.js"]
