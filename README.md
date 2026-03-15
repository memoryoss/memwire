# MemWire

<p align="center">
  <img src="docs/images/banner.png" alt="MemWire" width="100%" />
</p>

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
    qdrant_path="./memwire_data",  # local vector store
    qdrant_collection_prefix="app_",
)
memory = MemWire(config=config)

USER_ID = "alice"

# Add messages to memory
records = memory.add(
    user_id=USER_ID,
    messages=[{"role": "user", "content": "I prefer dark mode and short answers."}],
)
for r in records:
    print(f"[stored] ({r.category}) {r.content}")

# Recall relevant context for a query
result = memory.recall("How should I format my answers?", user_id=USER_ID)
if result.formatted:
    print(result.formatted)
    # → "alice prefers dark mode and short answers."

# Inject recalled context into your LLM prompt
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
]
if result.formatted:
    messages.append(
        {"role": "system", "content": f"Memory context:\n{result.formatted}"}
    )
messages.append({"role": "user", "content": "How should I format my answers?"})

# After you get the LLM response, reinforce the memory paths that were used
memory.feedback(response="<assistant response here>", user_id=USER_ID)

# Search memories by keyword / semantic similarity
hits = memory.search("dark mode", user_id=USER_ID, top_k=5)
for record, score in hits:
    print(f"[{score:.2f}] ({record.category}) {record.content}")

# Inspect stats
stats = memory.get_stats(user_id=USER_ID)
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
    qdrant_collection_prefix="app_",
)
memory = MemWire(config=config)
```

---

### REST API

The `api/` folder provides a self-hosted REST API backed by FastAPI and Qdrant.

#### Start the server

```bash
cd api
docker compose up --build   # Qdrant + MemWire API on :8000
```

Interactive docs: **http://localhost:8000/docs**

---

#### Store memory

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

#### Recall context

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

#### Search memories

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

See [api/README.md](api/README.md) for configuration options and local development setup.

## Customization

MemWire is designed to be a building block. Everything is tunable via `MemWireConfig`:

```python
config = MemWireConfig(
    # --- Embedding ---
    model_name="BAAI/bge-small-en-v1.5",   # swap the dense embedding model
    embedding_dim=384,

    # --- Storage ---
    org_id="my_org",                        # organisation identifier (multi-tenant)
    database_url="sqlite:///memory.db",     # SQLAlchemy URL; defaults to sqlite:///memwire_<org_id>.db

    # Use Qdrant Cloud instead of local
    qdrant_url="https://your-cluster.qdrant.io",
    qdrant_api_key="...",
    qdrant_collection_prefix="myapp_",

    # --- Search quality ---
    use_hybrid_search=True,     # dense + sparse (SPLADE) retrieval
    use_reranking=True,         # cross-encoder reranking for higher precision
    reranker_model_name="Xenova/ms-marco-MiniLM-L-6-v2",

    # --- Recall tuning ---
    recall_min_relevance=0.3,   # raise to be more selective (default 0.25)
    recall_max_paths=10,        # max memory paths returned
    recall_max_depth=4,         # BFS depth in the displacement graph
    tension_threshold=0.6,      # lower to catch contradictions earlier
    recency_weight=0.3,         # how much recency boosts recall score
    recency_halflife=7200.0,    # seconds before a memory's recency score halves

    # --- Graph construction ---
    displacement_threshold=0.15,   # minimum displacement to create a graph edge
    node_merge_similarity=0.85,    # cosine threshold for deduplicating nodes

    # --- Feedback loop ---
    feedback_strengthen_rate=0.1,  # how much a good response reinforces edges
    feedback_weaken_rate=0.05,     # how much unused edges decay

    # --- Memory classification ---
    # Extend or replace the built-in categories (fact, preference, instruction, event, entity)
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


## Supported LLMs

MemWire is model-agnostic. Memory operations like storage, recall, and search work with any language model or provider.

| Provider | Example |
|---|---|
| OpenAI | [examples/openai/](examples/openai/) |
| Azure OpenAI | [examples/azure-openai/](examples/azure-openai/) |
| Anthropic, Gemini, Ollama, or any other | Pass the recalled context into any LLM |


## Roadmap

See [ROADMAP.md](ROADMAP.md) for the full plan.


## Contributing

PRs and issues are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) and [GOVERNANCE.md](GOVERNANCE.md).

## License

Apache License 2.0
