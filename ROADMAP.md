# MemWire Roadmap

## 📌 Status Legend

| Status | Meaning |
| --- | --- |
| ✅ Completed | Implemented and stable |
| 🚧 In Progress | Actively being developed |
| 🟡 Planned | Approved and prioritized |
| 💡 Research | Under exploration |
| 🤝 Community | Contribution welcome |

---

# 🎯 Vision

MemWire aims to become:

> A self-hosted, model-agnostic memory infrastructure for AI agents  deployable on-premise or in any cloud.
> 

---

# 📦 Phase 1 — Core Infrastructure (MVP)

**Goal:** Production-ready, self-hosted memory API.

| Feature | Description | Status | Priority |
| --- | --- | --- | --- |
| Memory Store | PostgreSQL and QDrant based structured memory schema | 🚧 | High |
| Vector Pipeline | Embedding-only mode (no LLM required) | 🟡 | High |
| REST API | Store, retrieve and search endpoints | 🚧 | High |
| Multi-Tenant Support | `app_id`, `user_id`, `workspace_id` isolation | 🟡 | High |
| Explicit Fact Recording | Structured fact memory model | 🟡 | High |
| Docker Deployment | Local-first setup | 🟡 | High |
| Ollama Support | Local embeddings & LLM support | 🟡 | Medium |

---

# 🧠 Phase 2 — Intelligent Memory Layer

**Goal:** Move from storage → intelligent memory management.

| Feature | Description | Status | Priority |
| --- | --- | --- | --- |
| Agentic Fact Extraction | LLM-based structured memory extraction | 💡 | High |
| Knowledge Ingestion | PDF / DOCX / URL ingestion | 🟡 | High |
| Context Assembly Engine | Ranking + relevance scoring | 💡 | High |
| Fact Merging | Deduplication & updates | 💡 | Medium |
| Memory Metadata | Tags, categories, custom instructions | 🟡 | Medium |
| Python SDK | Developer-friendly integration | 🟡 | High |
| Basic Dashboard | Memory inspection UI | 🤝 | Medium |

---

# ⚡ Phase 3 — Augmented Memory Layer (v3 Concept)

**Goal:** Adaptive long-lived AI memory.

| Feature | Description | Status | Priority |
| --- | --- | --- | --- |
| Memory Ranking Engine | Intelligent scoring | 💡 | High |
| Memory Decay Policies | Relevance aging | 💡 | Medium |
| Conflict Resolution | Fact versioning | 💡 | Medium |
| Prompt Budget Optimization | Reduce token waste | 💡 | High |
| Memory Analytics | Usage insights | 🤝 | Medium |
| Debug Mode | Inspect context assembly | 🤝 | Medium |

---

# 🌍 Phase 4 — Distributed & Advanced Capabilities

| Feature | Description | Status | Priority |
| --- | --- | --- | --- |
| Pluggable Vector Backends | Abstract vector layer | 💡 | Medium |
| Cross-Node Memory Sync | Federated memory research | 💡 | Low |
| Event Hooks | Webhooks for memory updates | 🟡 | Medium |
| Memory Snapshots | Export/import memory states | 💡 | Medium |

---

# 🔌 Integrations

## 🗄 Database Connectors

| Database | Type | Purpose | Status |
| --- | --- | --- | --- |
| PostgreSQL | Relational | Primary SQL memory store | 🚧 |
| pgvector | Extension | Vector indexing | 🚧 |
| MySQL | Relational | Optional SQL backend | 💡 |
| SQLite | Embedded | Lightweight local mode | 💡 |
| Neon | Serverless Postgres | Cloud-native Postgres | 💡 |

---

## 📦 Vector Storage Connectors

| Provider | Type | Use Case | Status |
| --- | --- | --- | --- |
| pgvector | Embedded | Default vector index | 🚧 |
| Qdrant | External | High-scale vector search | 💡 |
| Weaviate | External | Hybrid vector search | 💡 |
| Pinecone | Managed | SaaS vector DB | 💡 |
| Milvus | Distributed | Large-scale deployments | 💡 |

---

## 🗃 Object & File Storage

| Provider | Use Case | Status |
| --- | --- | --- |
| Local Filesystem | Document ingestion | 🟡 |
| S3-Compatible | Knowledge storage | 💡 |
| Azure Blob Storage | Enterprise deployments | 💡 |
| GCS | Cloud-native storage | 💡 |

---

## 🤖 LLM & Embedding Providers

| Provider | Mode | Status |
| --- | --- | --- |
| Ollama | Local | 🟡 |
| OpenAI | Cloud | 💡 |
| Anthropic | Cloud | 💡 |
| Gemini | Cloud | 💡 |
| Pydantic AI | Abstraction layer | 💡 |
| Azure OpenAI | Enterprise | 💡 |

---

# 🧠 Agent Framework Integrations

MemWire is framework-agnostic.

| Framework | Integration Type | Example Use Case | Status |
| --- | --- | --- | --- |
| LangChain | Memory backend | Replace ConversationBufferMemory | 💡 |
| CrewAI | Persistent agent memory | Long-lived agents | 💡 |
| Agno | Memory provider | Structured fact memory | 💡 |
| AutoGen | Multi-agent state storage | Shared memory workspace | 💡 |
| Semantic Kernel | Context retrieval layer | Enterprise copilots | 💡 |
| Custom Agents | Direct API usage | Any AI system | 🟡 |

---

# 🛠 Infrastructure & Dev Experience

| Feature | Description | Status |
| --- | --- | --- |
| CI/CD | Automated tests & linting | 🟡 |
| Test Coverage | Unit + integration tests | 🟡 |
| OpenAPI Docs | Swagger documentation | 🟡 |
| Helm Charts | Kubernetes deployment | 🤝 |
| Terraform Examples | Cloud deployment | 🤝 |
| Example Chat App | Demo integration | 🟡 |

---

# 🔐 Enterprise & Security (Long-Term)

| Feature | Description | Status |
| --- | --- | --- |
| RBAC | Role-based access control | 💡 |
| Encryption at Rest | Secure memory storage | 💡 |
| Audit Logs | Access & mutation logging | 💡 |
| Retention Policies | Memory lifecycle rules | 💡 |
| Compliance Mode | Enterprise governance | 💡 |

---

# 📅 Release Strategy

- Minor releases: Every 4–6 weeks
- Major releases: Feature milestone-based
- Experimental features behind flags

---

# 🤝 Contributing

We welcome contributors.

You can help with:

- Vector abstraction layer
- Ranking algorithms
- Ingestion performance
- Framework adapters
- Documentation improvements

Open discussions and RFCs encouraged.

---

# 🧠 Long-Term Direction

MemWire evolves from:

Memory Storage

→ Intelligent Memory Management

→ Augmented Memory Infrastructure

→ Distributed Memory Systems