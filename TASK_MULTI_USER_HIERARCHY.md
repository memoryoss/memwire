# Task: Multi-User Hierarchical Memory Support

**Priority:** High  
**Area:** Core API, Storage, Config  
**Files affected:** `memwire/config.py`, `memwire/api/client.py`, `memwire/storage/models.py`, `memwire/storage/database.py`, `memwire/storage/qdrant_store.py`, `memwire/core/engine.py`

---

## Background

Currently, `MemWire` is scoped to a single user. `user_id` lives both in `MemWireConfig` and in the `MemWire(user_id=...)` constructor, and the entire DB/Qdrant collection is for one user. This needs to evolve into a **4-level hierarchy** so a single `MemWire` instance (and one database) can serve an entire organization with multiple projects, apps, and users.

---

## Target Architecture

```
orgId          ← defined in MemWireConfig — one DB/Qdrant namespace per org
  └── workspaceId / projectId   ← org has multiple projects
        └── appId               ← each project has one or more apps
              └── userId        ← each app has many users
```

Each level is optional when calling `add()` / `recall()`. When a level is omitted, behaviour is scoped to the levels that were provided (see API section below).

---

## Required Changes

### 1. `MemWireConfig` — replace `user_id` with `org_id`

**Current:**
```python
@dataclass
class MemWireConfig:
    ...
    user_id: str = "default"

    def get_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return f"sqlite:///memwire_{self.user_id}.db"
```

**Target:**
```python
@dataclass
class MemWireConfig:
    ...
    org_id: str = "default"   # replaces user_id

    def get_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return f"sqlite:///memwire_{self.org_id}.db"
```

**Callsite change** (demo apps and tests):
```python
# Before
config = MemWireConfig(
    user_id="chat_user",
    database_url="sqlite:///chat_memory.db",
    qdrant_url=qdrant_url,
    qdrant_collection_prefix="chat_",
)

# After
config = MemWireConfig(
    org_id="my_org",          # identifies the organisation; one DB per org
    database_url="sqlite:///chat_memory.db",
    qdrant_url=qdrant_url,
    qdrant_collection_prefix="chat_",
)
```

---

### 2. `MemWire.__init__` — remove `user_id`, accept only `config`

**Current:**
```python
class MemWire:
    def __init__(
        self,
        user_id: str = "default",
        agent_id: Optional[str] = None,
        config: Optional[MemWireConfig] = None,
    ):
        self.config = config or MemWireConfig()
        self.config.user_id = user_id   # mutates config
        self.user_id = user_id
```

**Target:**
```python
class MemWire:
    def __init__(self, config: Optional[MemWireConfig] = None):
        self.config = config or MemWireConfig()
        # org_id is read from self.config.org_id — no mutation here
```

**Callsite change:**
```python
# Before
memory = MemWire(user_id="chat_user", config=config)

# After
memory = MemWire(config=config)
```

---

### 3. `MemWire.add()` — hierarchical routing signature

The method must accept `userId`, `appId`, and `workspaceId` as **positional-or-keyword** arguments so callers can pass only the levels they care about.

**Target signatures (all valid):**
```python
# Level 1 — user only
memory.add(userId, messages=[...])

# Level 2 — user + app
memory.add(userId, appId, messages=[...])

# Level 3 — user + app + workspace
memory.add(userId, appId, workspaceId, messages=[...])
```

**Recommended implementation:**
```python
def add(
    self,
    user_id: str,
    app_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    *,
    messages: list[dict[str, str]],
) -> list[MemoryRecord]:
    """
    Add memories for a given user within the org defined in config.

    Args:
        user_id:      Required. The end-user whose memory is being stored.
        app_id:       Optional. The application context within a workspace.
        workspace_id: Optional. The workspace / project context within the org.
        messages:     List of {"role": ..., "content": ...} dicts.
    """
    ...
```

> **Note:** `workspace_id` maps to what Bobur also calls `projectId`. Use `workspace_id` in the Python API and document the alias.

---

### 4. `MemWire.recall()` and `MemWire.feedback()` — same hierarchical signature

Recall must be scoped to the same hierarchy used at write time, otherwise cross-user leakage occurs.

```python
def recall(
    self,
    query: str,
    user_id: str,
    app_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    top_k: int = 5,
) -> RecallResult:
    ...

def feedback(
    self,
    response: str,
    user_id: str,
    app_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
) -> None:
    ...
```

---

### 5. Storage models — add hierarchy columns

#### `MemoryModel` (SQLAlchemy — `memwire/storage/models.py`)

Add `org_id`, `workspace_id`, `app_id`; keep `user_id`:

```python
class MemoryModel(Base):
    __tablename__ = "memories"

    memory_id    = Column(String, primary_key=True)
    org_id       = Column(String, nullable=False, index=True)   # NEW
    workspace_id = Column(String, nullable=True,  index=True)   # NEW
    app_id       = Column(String, nullable=True,  index=True)   # NEW
    user_id      = Column(String, nullable=False, index=True)   # existing
    ...
```

Add a **composite index** for the common lookup pattern:

```python
from sqlalchemy import Index

Index("ix_memories_hierarchy", "org_id", "workspace_id", "app_id", "user_id")
```

#### `AnchorModel`

Add `org_id`, `workspace_id`, `app_id` alongside `user_id` to scope anchors correctly.

---

### 6. Qdrant collection naming — encode hierarchy

Currently the collection prefix is flat. Extend it to encode the full scope so memories are physically separated in Qdrant.

**Proposed convention:**
```
{prefix}{org_id}_{workspace_id}_{app_id}_{user_id}_memories
```

Levels that are `None` are replaced with `"_"` or omitted consistently. Centralise this logic in a helper in `QdrantStore`:

```python
def _collection_name(self, user_id: str, app_id: Optional[str], workspace_id: Optional[str]) -> str:
    parts = [self.config.qdrant_collection_prefix, self.config.org_id]
    if workspace_id:
        parts.append(workspace_id)
    if app_id:
        parts.append(app_id)
    parts.append(user_id)
    parts.append("memories")
    return "_".join(parts)
```

> **Alternative:** Keep a single collection per org and use Qdrant **payload filtering** (`org_id`, `workspace_id`, `app_id`, `user_id`). This avoids collection proliferation and is easier to query across scopes. **Recommended for v1.**

---

### 7. Alembic migration

A new Alembic revision must be created to:
1. Add `org_id`, `workspace_id`, `app_id` columns to `memories` and `anchors` tables.
2. Backfill `org_id` with `"default"` for all existing rows.
3. Add the composite index `ix_memories_hierarchy`.

```bash
alembic revision --autogenerate -m "add_hierarchy_columns"
```

---

### 8. Update `DatabaseManager` query methods

Any method that currently filters by `user_id` must be updated to filter by all provided hierarchy levels:

```python
def get_memories(
    self,
    user_id: str,
    org_id: str,
    app_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
) -> list[MemoryModel]:
    filters = [
        MemoryModel.org_id == org_id,
        MemoryModel.user_id == user_id,
    ]
    if workspace_id is not None:
        filters.append(MemoryModel.workspace_id == workspace_id)
    if app_id is not None:
        filters.append(MemoryModel.app_id == app_id)
    ...
```

---

## Demo App Changes (`chat_azure.py` / `web_chat_azure.py`)

```python
# Config — org_id, not user_id
config = MemWireConfig(
    org_id="demo_org",
    database_url="sqlite:///chat_memory.db",
    qdrant_url=qdrant_url,
    qdrant_path=None if qdrant_url else "chat_qdrant",
    qdrant_collection_prefix="chat_",
)

# Instantiation — no user_id arg
memory = MemWire(config=config)

# Adding memories with userId
memory.add(
    "alice",                   # userId
    messages=[
        {"role": "user",      "content": user_input},
        {"role": "assistant", "content": assistant_msg},
    ],
)

# Adding memories with userId + appId
memory.add(
    "alice",
    "chatbot_v2",              # appId
    messages=[...],
)

# Recall
result = memory.recall(user_input, user_id="alice")
```

---

## Backwards Compatibility

- Keep a **deprecation shim** for existing `MemWire(user_id=..., config=...)` callers: accept the old signature but emit a `DeprecationWarning` and map `user_id` → `config.org_id` so existing code doesn't break immediately.
- Keep a shim in `MemWireConfig` that accepts `user_id` and maps it to `org_id` with a deprecation warning.
- Remove both shims in the next minor version after this lands.

---

## Acceptance Criteria

- [ ] `MemWireConfig` has `org_id`; `user_id` is gone (or deprecated shim only)
- [ ] `MemWire(config=config)` works; `user_id` arg is gone (or deprecated shim)
- [ ] `memory.add(userId, messages=[...])` stores with `user_id` scoped under `config.org_id`
- [ ] `memory.add(userId, appId, messages=[...])` stores with `app_id` column populated
- [ ] `memory.add(userId, appId, workspaceId, messages=[...])` stores with all three columns populated
- [ ] `memory.recall(query, userId)` returns memories scoped to that user only — no cross-user leakage
- [ ] `memory.recall(query, userId, appId, workspaceId)` scopes recall to exact hierarchy level
- [ ] Alembic migration runs cleanly on a fresh DB and on an existing `v0.2.0` DB
- [ ] All existing tests pass (with shims active)
- [ ] New unit tests cover each `add()` signature variant and verify isolation between users and apps
- [ ] `chat_azure.py` and `web_chat_azure.py` demos updated to new API
- [ ] README updated with new usage examples

---

## Open Questions

1. **Single collection vs. per-user collection in Qdrant?** Payload filtering (single collection) is recommended for v1 to avoid collection proliferation. Confirm with team.
2. **`workspaceId` vs. `projectId` naming?** The Python API will use `workspace_id`; document `projectId` as an alias in the README. Confirm whether to expose both or just one.
3. **Cross-scope recall?** Should `recall(query, userId=None, appId="chatbot_v2")` be supported to retrieve memories across all users of an app? Out of scope for this task but worth noting for v2.
