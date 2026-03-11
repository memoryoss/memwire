FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Install third-party deps first (layer cache)
COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install memwire from local source
COPY pyproject.toml ./
COPY memwire/ memwire/
RUN pip install --no-cache-dir .

# Copy API entrypoint
COPY api/main.py ./

# Data directory for SQLite + embedded Qdrant
RUN mkdir -p /data

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
