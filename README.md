# MemWire

> Self-hosted memory infrastructure for AI agents. Bring your own LLM, your own database — deploy persistent memory to any cloud.

---

## Quick Start

```bash
git clone https://github.com/memoryoss/memwire
cd memwire
./memwire.sh start
```

On first run, `memwire.sh` copies `api/sample.env` → `api/.env` and prompts for your LLM provider.

No API key needed — MemWire runs fully locally with Ollama. Models are pulled automatically on first start.

| Service | URL |
|---|---|
| Dashboard | http://localhost:3000 |
| API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |

---

## What MemWire Does

MemWire is a memory and context API. Your agent calls MemWire to store conversations and retrieve enriched context.

---

## Using the API

All requests require an `Authorization: Bearer <api_key>` header. The bootstrap key (`memwire-bootstrap`) is available on first run — create a permanent key in the dashboard **Settings → API Keys**.

### Store a memory

```bash
curl -X POST http://localhost:8000/v1/memory/store \
  -H "Authorization: Bearer memwire-bootstrap" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "my-agent",
    "user_id":  "user-123",
    "user_message":      "I prefer concise answers and I work in Python.",
    "assistant_message": "Got it, I will keep that in mind."
  }'
```

```json
{ "success": true, "memory_id": "a1b2c3d4-..." }
```

### Retrieve memories for an agent

```bash
curl "http://localhost:8000/v1/memory/retrieve?agent_id=my-agent&user_id=user-123" \
  -H "Authorization: Bearer memwire-bootstrap"
```

```json
{
  "memories": [
    {
      "id": "a1b2c3d4-...",
      "memory": "User prefers concise answers and works in Python.",
      "topics": ["preferences", "programming"],
      "user_id": "user-123",
      "timestamp": "2026-02-23T08:12:28Z"
    }
  ],
  "total": 1
}
```

### Search memories

```bash
curl -X POST http://localhost:8000/v1/memory/search \
  -H "Authorization: Bearer memwire-bootstrap" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "my-agent",
    "user_id":  "user-123",
    "query":    "programming language preferences",
    "limit":    5
  }'
```

---

## CLI Commands

```bash
./memwire.sh start     # Start all services (sets up .env on first run)
./memwire.sh stop      # Stop all services
./memwire.sh build     # Build Docker images from source
./memwire.sh logs      # Tail all service logs
./memwire.sh status    # Show running service status
./memwire.sh reset     # Destroy all containers and volumes
```

---

## Supported LLM Providers

| Provider | `LLM_PROVIDER` | Example `LLM_MODEL` | Notes |
|---|---|---|---|
| Ollama (local) | `ollama` | `llama3.2` | Any model served by Ollama — llama3.2, mistral, phi3, gemma3 … No API key needed |
| OpenAI | `openai` | `gpt-4o` | Requires `LLM_API_KEY` |
| Azure OpenAI | `azure_openai` | `gpt-4o` | Requires `LLM_API_KEY`, `LLM_BASE_URL`, `AZURE_API_VERSION` |

Configure via `api/.env`:

**Ollama (local)**
```env
LLM_PROVIDER=ollama
LLM_MODEL=llama3.2
LLM_BASE_URL=http://ollama:11434
```

**OpenAI**
```env
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
LLM_API_KEY=sk-...
```

**Azure OpenAI**
```env
LLM_PROVIDER=azure_openai
LLM_MODEL=gpt-4o
LLM_API_KEY=your-azure-api-key
LLM_BASE_URL=https://<resource>.openai.azure.com/
AZURE_API_VERSION=2024-12-01-preview
```

---

## Supported Embedders

Embeddings power semantic memory search and the knowledge base vector store.

| Provider | `LLM_PROVIDER` | Model | Dimensions | Notes |
|---|---|---|---|---|
| Ollama (local) | `ollama` | `nomic-embed-text` | 768 | No API key needed |
| OpenAI | `openai` | `text-embedding-3-small` | 1536 | Recommended for production |
| OpenAI | `openai` | `text-embedding-3-large` | 3072 | Highest accuracy |
| Azure OpenAI | `azure_openai` | `text-embedding-ada-002` | 1536 | Azure-hosted OpenAI embeddings |

The embedder is automatically selected based on `LLM_PROVIDER`. Override with:

```env
# Ollama
EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_DIMENSIONS=768

# OpenAI
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536

# Azure OpenAI
EMBEDDING_MODEL=text-embedding-ada-002
EMBEDDING_DIMENSIONS=1536
```

---

## Database

MemWire uses PostgreSQL with the [pgvector](https://github.com/pgvector/pgvector) extension. A pre-configured container is included — no setup required.

| Option | Notes |
|---|---|
| **Bundled (default)** | `pgvector/pgvector:pg16` container — starts automatically with `USE_BUNDLED_DB=true` |

```env
USE_BUNDLED_DB=true
DATABASE_URL=postgresql://memwire:memwire@db:5432/memwire
```

---

## Architecture

| Container | Image | Role |
|---|---|---|
| `memwire-api` | `memwire/api` | FastAPI memory + knowledge API |
| `memwire-ui` | `memwire/ui` | React developer dashboard (nginx) |
| `memwire-db` | `pgvector/pgvector:pg16` | PostgreSQL + pgvector |
| `memwire-ollama` | `ollama/ollama:latest` | Local LLM + embedder (optional — enabled when `LLM_PROVIDER=ollama`) |

Built with [Agno](https://github.com/agno-agi/agno) for memory and knowledge abstractions.

---

## License

MIT
