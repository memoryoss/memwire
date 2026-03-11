# MemWire REST API

A self-hosted REST API that provides persistent AI memory infrastructure for an organisation.

| Endpoint | Method | Description |
|---|---|---|
| `/v1/memory` | POST | Store messages into a user's memory |
| `/v1/memory/recall` | POST | Recall relevant context for a query |
| `/v1/memory/search` | POST | Search memories by semantic similarity |
| `/health` | GET | Health check |

Interactive docs available at **http://localhost:8000/docs** once running.

---

## Run with Docker

```bash
docker compose up --build
```

Then open http://localhost:8000/docs.

To stop:

```bash
docker compose down
```

---

## Run locally

```bash
# From the project root
pip install -e ".[chat]"
cd api
uvicorn main:app --reload
```

---

## Endpoints

### Store memory

```bash
curl -X POST http://localhost:8000/v1/memory \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "alice",
    "app_id": "app_a",
    "workspace_id": "team_1",
    "messages": [
      { "role": "user", "content": "I prefer dark mode and short answers." }
    ]
  }'
```

```json
{
  "stored": 1,
  "memory_ids": ["mem_3f7a1c2d9e4b"]
}
```

---

### Recall context

```bash
curl -X POST http://localhost:8000/v1/memory/recall \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "alice",
    "app_id": "app_a",
    "workspace_id": "team_1",
    "query": "How should I format my answers?"
  }'
```

```json
{
  "context": "alice prefers dark mode and short answers.",
  "paths": 2,
  "knowledge": []
}
```

---

### Search memories

```bash
curl -X POST http://localhost:8000/v1/memory/search \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "alice",
    "app_id": "app_a",
    "workspace_id": "team_1",
    "query": "dark mode",
    "top_k": 10
  }'
```

```json
{
  "results": [
    {
      "memory_id": "mem_3f7a1c2d9e4b",
      "content": "I prefer dark mode and short answers.",
      "category": "preference",
      "score": 0.94
    }
  ]
}
```

---

## Configuration

All settings are controlled via environment variables:

| Variable | Default | Description |
|---|---|---|
| `QDRANT_URL` | — | Qdrant server URL (e.g. `http://localhost:6333`). Omit to use embedded mode. |
| `QDRANT_PATH` | `/data/qdrant` | Path for embedded Qdrant storage (ignored when `QDRANT_URL` is set) |
| `DATABASE_URL` | `sqlite:////data/memwire.db` | SQLAlchemy-compatible database URL |
| `ORG_ID` | `default` | Organisation identifier for multi-tenant isolation |
| `QDRANT_COLLECTION_PREFIX` | `mw_` | Prefix for Qdrant collection names |
