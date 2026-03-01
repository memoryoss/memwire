FROM python:3.12-slim

WORKDIR /app

# Install only the essentials
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Install Python deps first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY pyproject.toml alembic.ini ./
COPY memwire/ memwire/
COPY examples/web_chat.py examples/chat.py ./

# Data directory for SQLite metadata
RUN mkdir -p /data

EXPOSE 8000

CMD ["uvicorn", "web_chat:app", "--host", "0.0.0.0", "--port", "8000"]
