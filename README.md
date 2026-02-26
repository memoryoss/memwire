# MemWire

> Enterprise-grade, self-hosted memory infrastructure for AI agents. Deploy persistent AI memory on-premise or in any cloud with your own LLM and database.

**v0.2.0** | 97/97 tests passing | 77.9% accuracy on LOCOMO benchmark (#1)

---

## Features

- **Displacement graph** — conversation turns become graph nodes linked by embedding displacement, not keyword matching
- **Path-based recall** — BFS traversal finds relevant memory paths with tension detection
- **Hybrid search** — dense (MiniLM-L6-v2) + sparse (SPLADE) embeddings with optional reranking
- **Knowledge base** — chunk and search .txt files alongside conversational memory
- **Multi-tenant** — `user_id` + optional `agent_id` isolation
- **Zero-LLM overhead** — classification via anchor centroids, no API calls for memory operations

---

## Quick Start

### Docker (recommended)

One command starts all services — API, dashboard, database, and optional local LLM:

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

### Manual Setup

```bash
pip install -r requirements.txt
cp .env.example .env       # add your OpenAI API key
docker compose up -d       # starts Qdrant + MemWire web UI
```

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

### Retrieve memories

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

## Python Library

Use MemWire directly as a Python library:

```python
from memwire import MemWire, MemWireConfig

# With Qdrant server
config = MemWireConfig(qdrant_url="http://localhost:6333")
memory = MemWire(user_id="alice", config=config)

# Or embedded mode
memory = MemWire(user_id="alice", config=MemWireConfig(qdrant_path=":memory:"))

# Store a conversation turn
memory.add([
    {"role": "user", "content": "I prefer dark mode in all my editors"},
    {"role": "assistant", "content": "Noted, you prefer dark mode."}
])

# Recall relevant memories
result = memory.recall("What are the user's UI preferences?")
for path in result.paths:
    print(path.summary, f"(relevance: {path.relevance:.2f})")

# Provide feedback to strengthen/weaken edges
memory.feedback(response="The user prefers dark mode for all editors")

# Knowledge base
memory.add_knowledge("company_policy.txt", chunk_text)
results = memory.search_knowledge("vacation policy")
```

### API Reference

| Method | Description |
|--------|-------------|
| `MemWire(user_id, agent_id?, config?)` | Initialize memory for a user |
| `.add(messages)` | Store conversation messages |
| `.recall(query)` | Retrieve relevant memory paths + knowledge |
| `.feedback(response)` | Reinforce/weaken graph edges based on response |
| `.search(query, top_k?)` | Direct vector similarity search |
| `.add_anchor(name, examples)` | Add a classification anchor |
| `.add_knowledge(source, text)` | Add a knowledge base chunk |
| `.search_knowledge(query, top_k?)` | Search knowledge base |
| `.delete_knowledge(source)` | Delete knowledge by source name |

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

## Chat Apps

### CLI Chat

```bash
python chat.py
```

Supports inline knowledge base commands:

- `kb load <file.txt>` — load a text file into the knowledge base
- `kb search <query>` — search the knowledge base
- `kb list` — list loaded knowledge sources

### Web Chat

```bash
python web_chat.py
```

Opens at `http://localhost:8000` with streaming chat, memory visualization, knowledge base upload, and performance metrics.

---

## Configuration

### LLM Providers

| Provider | `LLM_PROVIDER` | Example `LLM_MODEL` | Notes |
|---|---|---|---|
| Ollama (local) | `ollama` | `llama3.2` | Any model served by Ollama — no API key needed |
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

### Embedders

| Provider | `LLM_PROVIDER` | Model | Dimensions | Notes |
|---|---|---|---|---|
| Ollama (local) | `ollama` | `nomic-embed-text` | 768 | No API key needed |
| OpenAI | `openai` | `text-embedding-3-small` | 1536 | Recommended for production |
| OpenAI | `openai` | `text-embedding-3-large` | 3072 | Highest accuracy |
| Azure OpenAI | `azure_openai` | `text-embedding-ada-002` | 1536 | Azure-hosted OpenAI embeddings |

Override with:

```env
EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_DIMENSIONS=768
```

### MemWireConfig (Library)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `model_name` | `all-MiniLM-L6-v2` | Dense embedding model |
| `sparse_model_name` | `Splade_PP_en_v1` | Sparse embedding model |
| `qdrant_url` | `None` | Qdrant server URL |
| `qdrant_path` | `None` | Local Qdrant path (embedded mode) |
| `use_hybrid_search` | `True` | Enable dense + sparse fusion |
| `use_reranking` | `False` | Enable cross-encoder reranking |
| `node_merge_similarity` | `0.85` | Threshold for deduplicating graph nodes |
| `displacement_threshold` | `0.15` | Min displacement to create graph edges |
| `recall_max_depth` | `4` | Max BFS depth for recall |
| `recall_seed_top_k` | `5` | Number of seed nodes for recall |

See `memwire/config.py` for the full list.

---

## Database

MemWire uses PostgreSQL with the [pgvector](https://github.com/pgvector/pgvector) extension. A pre-configured container is included — no setup required.

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

## Running Tests

```bash
python -m pytest tests/ -x -q
```

Tests use Qdrant in-memory mode — no server required.

---

## Project Structure

```
memwire/
├── memwire/                 # Core package
│   ├── api/                 #   Public API (MemWire client)
│   ├── core/                #   Embeddings, graph, recall, classifier, reranker
│   ├── storage/             #   Qdrant store, SQLite models, vector ops
│   ├── migrations/          #   Alembic migrations
│   ├── utils/               #   Types, math ops
│   └── config.py            #   MemWireConfig
├── tests/                   # Test suite (97 tests)
├── benchmark/               # LOCOMO benchmark suite
├── chat.py                  # CLI chat app
├── web_chat.py              # Web chat app (FastAPI)
├── pyproject.toml
├── requirements.txt
└── alembic.ini
```

---

## License

MIT
