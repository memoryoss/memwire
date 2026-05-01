# syntax=docker/dockerfile:1.6

# ============================
# Stage 1: Build Studio (Vite)
# ============================
FROM node:20-alpine AS studio-builder

WORKDIR /studio

COPY studio/package*.json ./
RUN npm ci --no-audit --no-fund

COPY studio/ ./
RUN npm run build

# ============================
# Stage 2: Python runtime
# ============================
FROM python:3.12-slim AS runtime

ARG INSTALL_INGEST=true

WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY memwire/ ./memwire/

RUN pip install --no-cache-dir --upgrade pip \
 && if [ "$INSTALL_INGEST" = "true" ]; then \
        pip install --no-cache-dir ".[server,ingest]"; \
    else \
        pip install --no-cache-dir ".[server]"; \
    fi

COPY --from=studio-builder /studio/dist ./studio-static

RUN mkdir -p /data

ENV PYTHONUNBUFFERED=1
ENV PORT=8000
ENV STUDIO_STATIC_DIR=/app/studio-static
ENV DATABASE_URL=sqlite:////data/memwire.db

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=20s \
    CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["uvicorn", "memwire.server.app:app", "--host", "0.0.0.0", "--port", "8000"]
