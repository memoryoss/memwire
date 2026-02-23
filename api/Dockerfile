FROM python:3.12-slim-bookworm AS base

ARG VERSION=dev
LABEL maintainer="ChatMemory" \
      description="MemWire API Service" \
      version="${VERSION}"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    APP_HOME=/app

RUN apt-get update \
    && apt-get --no-install-recommends install -y \
        build-essential \
        libmagic-dev \
        libssl-dev \
        pkg-config \
        curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR ${APP_HOME}

# ── Dependency cache stage ────────────────────
FROM base AS dependencies

COPY api/pyproject.toml api/requirements.txt ./

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ── Production stage ──────────────────────────
FROM dependencies AS production

COPY api/ ./

RUN chmod +x entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
CMD []
