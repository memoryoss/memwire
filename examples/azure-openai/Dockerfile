FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Install Python deps first (layer cache)
COPY examples/azure-openai/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy and install memwire from local source
COPY pyproject.toml ./
COPY memwire/ memwire/
RUN pip install --no-cache-dir .

# Copy application code
COPY examples/azure-openai/web_chat.py ./

# Data directory for SQLite metadata
RUN mkdir -p /data

EXPOSE 8000

CMD ["uvicorn", "web_chat:app", "--host", "0.0.0.0", "--port", "8000"]
