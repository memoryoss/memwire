FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt pyproject.toml ./
COPY memwire/ memwire/
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir ".[server]"

RUN mkdir -p /data

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "memwire.server.app:app", "--host", "0.0.0.0", "--port", "8000"]
