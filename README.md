# MemWire

> Enterprise-grade, self-hosted AI memory infrastructure layer. Deploy persistent AI memory on-premise or in any cloud with your own LLM and database.

![Self-Hosted](https://img.shields.io/badge/Self--Hosted-Yes-blue)
![Customizable](https://img.shields.io/badge/Customizable-Fully-green)
![Model-Agnostic](https://img.shields.io/badge/Model--Agnostic-Any%20LLM-orange)
![License](https://img.shields.io/badge/License-Apache%202.0-blue)

## What is MemWire?

MemWire is **an open source & enterprise-ready** AI memory infrastructure layer. MemWire gives your AI applications persistent, auditable memory with structured, updatable facts, **fastest** semantic retrieval across conversations and knowledge using **graph-based memory**.

- Fully customizable — adapt schemas, memory types, and pipelines to your use case
- Self-hosted — run entirely on your local machine, on-premise or in your own cloud
- Multi-tenant — isolate applications, users, and workspaces securely
- Bring your own database — PostgreSQL pgvector, Qdrant, Pinecone, ChromaDB, Weawiate or your preferred stack
- Bring your own LLM — OpenAI, Anthropic, Gemini, Ollama, or any provider
- Deploy anywhere — edge, private cloud, public cloud, air-gapped environments
- Knowledge ingestion — ingest documents (PDF, Excel, CSV, etc.) alongside conversation memory; recalled together at query time
- Auditable — every memory is traceable, categorized (fact, preference, instruction, event, entity), and inspectable
- Contradiction detection — conflicting memories are automatically flagged, so your agent always reasons from a consistent state
- Feedback loop — reinforce memory paths that led to good responses; unused edges decay over time

---

## Quickstart

### Python SDK

#### Install

```bash
pip install memwire
```

---

#### Embedded mode

Data is stored on disk in `./memwire_data/`.

```python
from memwire import MemWire, MemWireConfig

config = MemWireConfig(
    qdrant_path="./memwire_data",          # local vector store
    database_url="sqlite:///memory.db",    # metadata ledger
    qdrant_collection_prefix="app_",
)
memory = MemWire(user_id="alice", config=config)

# Add messages to memory
memory.add([
    {"role": "user", "content": "I prefer dark mode and short answers."}
])

# Recall relevant context for a query
result = memory.recall("How should I format my answers?")
if result.formatted:
    print(result.formatted)
    # → "alice prefers dark mode and short answers."

# Inject recalled context into your LLM prompt
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
]
if result.formatted:
    messages.append({"role": "system", "content": f"Memory context:\n{result.formatted}"})
messages.append({"role": "user", "content": "How should I format my answers?"})

# After you get the LLM response, reinforce the memory paths that were used
memory.feedback(response="<assistant response here>")

# Search memories by keyword / semantic similarity
hits = memory.search("dark mode", top_k=5)
for record, score in hits:
    print(f"[{score:.2f}] ({record.category}) {record.content}")

# Inspect stats
stats = memory.get_stats()
print(stats)  # {"memories": 1, "nodes": ..., "edges": ..., "knowledge_bases": 0}

# Always close to flush background writes
memory.close()
```

---

#### With a local Qdrant server

```bash
docker run -p 6333:6333 qdrant/qdrant
```

```python
config = MemWireConfig(
    qdrant_url="http://localhost:6333",
    database_url="sqlite:///memory.db",
    qdrant_collection_prefix="app_",
)
memory = MemWire(user_id="alice", config=config)
```

---

### REST API

Start the server:

```bash
docker compose -f examples/docker-compose.yml up -d   # Qdrant + MemWire on :8000
```

---

#### Store memory

```bash
curl -X POST http://localhost:8000/v1/memory \
  -H "Content-Type: application/json" \
  -d '{
    "app_id": "app_a",
    "user_id": "alice",
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

#### Retrieve (recall) context

```bash
curl -X POST http://localhost:8000/v1/memory/recall \
  -H "Content-Type: application/json" \
  -d '{
    "app_id": "app_a",
    "user_id": "alice",
    "workspace_id": "team_1",
    "query": "How should I format my answers?",
    "top_k": 5
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

#### Search memories

```bash
curl -X POST http://localhost:8000/v1/memory/search \
  -H "Content-Type: application/json" \
  -d '{
    "app_id": "app_a",
    "user_id": "alice",
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

## Customization

MemWire is designed to be a building block, not a black box. Everything is tunable via `MemWireConfig`:

```python
config = MemWireConfig(
    # Swap the embedding model entirely
    model_name="BAAI/bge-small-en-v1.5",

    # Use Qdrant Cloud instead of local
    qdrant_url="https://your-cluster.qdrant.io",
    qdrant_api_key="...",

    # Enable reranking for higher precision
    use_reranking=True,
    reranker_model_name="Xenova/ms-marco-MiniLM-L-6-v2",

    # Tune memory sensitivity
    recall_min_relevance=0.3,   # raise to be more selective
    tension_threshold=0.7,       # lower to catch contradictions earlier
    recency_halflife=7200.0,     # how fast old memories decay

    # Add your own memory categories
    default_anchors={
        "product_feedback": ["The user complained about X", "They liked feature Y"],
        "tone": ["Always respond formally", "Use emojis"],
    },
)
```

## Supported databases

| Storage | Type | Status | Notes |
|---|---|---|---|
| [Qdrant](https://qdrant.tech) | Vector store | ✅ Supported | Embedded, local server, or Qdrant Cloud |


## Roadmap

See [ROADMAP.md](ROADMAP.md) for the full plan.


## Contributing

PRs and issues are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) and [GOVERNANCE.md](GOVERNANCE.md).

## License

Apache License 2.0
