"""
Memory Service

Pure Agno MemoryManager — no custom turns table.

All storage and retrieval go through Agno's MemoryManager which owns:
  agno.memories_{short}  — semantic memory facts (created/managed by Agno)
  agno.sessions_{short}  — session summaries   (created/managed by Agno)

Mirrors how chatmemory-backend works:
  store  → acreate_user_memories()
  fetch  → get_user_memories()
  delete → delete_user_memory()
"""

import uuid
import logging
from typing import Optional, List, Dict

from agno.db.postgres import PostgresDb
from agno.memory import MemoryManager
from agno.models.message import Message

from app.config import settings
from app.services.llm_service import get_model

logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _short(agent_id: str) -> str:
    """First segment of agent_id used as a short table suffix."""
    return agent_id.split("-")[0]


def get_memory_db(agent_id: str) -> PostgresDb:
    """
    Create a PostgresDb instance scoped to this agent.

    Agno auto-creates the following tables on first MemoryManager write:
      agno.memories_{short}  — semantic memory rows
      agno.sessions_{short}  — session summary rows
    """
    short = _short(agent_id)
    return PostgresDb(
        db_url=settings.DATABASE_URL,
        memory_table=f"memories_{short}",
        session_table=f"sessions_{short}",
        db_schema="agno",
    )


def _make_memory_manager(agent_id: str) -> MemoryManager:
    """Create a MemoryManager for an agent using the configured LLM model."""
    return MemoryManager(
        db=get_memory_db(agent_id),
        model=get_model(),
        system_message=(
            "Extract and remember key facts, preferences, and important context "
            "from this conversation. Focus on information useful for future interactions."
        ),
    )


# ── Public API ────────────────────────────────────────────────────────────────


async def store_memory(
    agent_id: str,
    user_id: str,
    user_message: str,
    assistant_message: Optional[str] = None,
    session_id: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> str:
    """
    Store conversation messages as Agno semantic memories.

    Calls MemoryManager.acreate_user_memories() — Agno extracts and persists
    semantic facts into agno.memories_{short} (creating the table if needed).

    Returns a generated ID used as the store response identifier.
    """
    memory_manager = _make_memory_manager(agent_id)

    messages = [Message(role="user", content=user_message)]
    if assistant_message:
        messages.append(Message(role="assistant", content=assistant_message))

    await memory_manager.acreate_user_memories(
        messages=messages,
        user_id=user_id,
        agent_id=agent_id,
    )

    return str(uuid.uuid4())


def get_history(
    agent_id: str,
    user_id: str,
    limit: int = 20,
    session_id: Optional[str] = None,
) -> List[Dict]:
    """
    Return Agno semantic memories for a user.

    Each item: { id, memory, topics, user_id, timestamp }

    session_id is accepted for API compatibility but Agno memories are not
    session-scoped at retrieval time.
    """
    try:
        memory_db = get_memory_db(agent_id)
        memory_manager = MemoryManager(db=memory_db)
        memories = memory_manager.get_user_memories(user_id=user_id) or []
    except Exception as exc:
        logger.warning(f"Could not fetch memories for agent={agent_id}: {exc}")
        return []

    result = []
    for m in memories[:limit]:
        # memory field may be a dict or a string depending on Agno version
        mem_obj = getattr(m, "memory", None)
        if isinstance(mem_obj, dict):
            mem_text = mem_obj.get("memory", str(mem_obj))
        elif mem_obj is not None:
            mem_text = str(mem_obj)
        else:
            mem_text = ""

        topics = getattr(m, "topics", None)
        topics_list = [str(t) for t in topics] if isinstance(topics, list) else []

        result.append(
            {
                "id": getattr(m, "memory_id", None) or str(uuid.uuid4()),
                "memory": mem_text,
                "topics": topics_list,
                "user_id": user_id,
                "timestamp": getattr(m, "updated_at", None)
                or getattr(m, "created_at", None),
            }
        )

    return result


def get_user_memories(agent_id: str, user_id: str) -> List[Dict]:
    """Return all Agno semantic memories for a user (no limit)."""
    return get_history(agent_id=agent_id, user_id=user_id, limit=10_000)


def search_memories(
    agent_id: str,
    query: str,
    user_id: Optional[str] = None,
    limit: int = 10,
) -> List[Dict]:
    """
    Search Agno semantic memories using MemoryManager.search_user_memories().

    Uses Agno's built-in vector/semantic search over agno.memories_{short}.
    Returns items in the same shape as get_history().
    """
    try:
        memory_db = get_memory_db(agent_id)
        memory_manager = MemoryManager(db=memory_db)
        results = (
            memory_manager.search_user_memories(
                query=query,
                user_id=user_id,
                limit=limit,
            )
            or []
        )
    except Exception as exc:
        logger.warning(f"search_memories failed for agent={agent_id}: {exc}")
        return []

    out = []
    for m in results:
        mem_obj = getattr(m, "memory", None)
        if isinstance(mem_obj, dict):
            mem_text = mem_obj.get("memory", str(mem_obj))
        elif mem_obj is not None:
            mem_text = str(mem_obj)
        else:
            mem_text = ""

        topics = getattr(m, "topics", None)
        topics_list = [str(t) for t in topics] if isinstance(topics, list) else []

        out.append(
            {
                "id": getattr(m, "memory_id", None) or str(uuid.uuid4()),
                "memory": mem_text,
                "topics": topics_list,
                "user_id": getattr(m, "user_id", None) or user_id or "",
                "timestamp": getattr(m, "updated_at", None)
                or getattr(m, "created_at", None),
            }
        )
    return out


def list_memories(
    agent_id: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = 100,
) -> List[Dict]:
    """
    List memories with optional filters.

    - agent_id + user_id  → query that agent's table filtered by user
    - agent_id only       → query that agent's table, all users
    - user_id only        → scan all memories_* tables for that user
    - neither             → scan all memories_* tables, return latest rows
    """
    from sqlalchemy import text
    from app.db_session import SessionLocal

    rows = []
    with SessionLocal() as db:
        try:
            if agent_id:
                # Query one specific agent table
                short = _short(agent_id)
                table = f'agno."memories_{short}"'
                sql = text(
                    f"SELECT memory_id, memory, topics, user_id, updated_at"
                    f" FROM {table}"
                    + (" WHERE user_id = :uid" if user_id else "")
                    + " ORDER BY updated_at DESC LIMIT :limit"
                )
                params: dict = {"limit": limit}
                if user_id:
                    params["uid"] = user_id
                rows = db.execute(sql, params).fetchall()
            else:
                # Scan all memories_* tables in agno schema
                tables = db.execute(
                    text(
                        "SELECT tablename FROM pg_tables"
                        " WHERE schemaname = 'agno' AND tablename LIKE 'memories_%'"
                    )
                ).fetchall()
                for (tname,) in tables:
                    try:
                        if user_id:
                            chunk = db.execute(
                                text(
                                    f"SELECT memory_id, memory, topics, user_id, updated_at"
                                    f' FROM agno."{tname}"'
                                    f" WHERE user_id = :uid"
                                    f" ORDER BY updated_at DESC LIMIT :limit"
                                ),
                                {"uid": user_id, "limit": limit},
                            ).fetchall()
                        else:
                            chunk = db.execute(
                                text(
                                    f"SELECT memory_id, memory, topics, user_id, updated_at"
                                    f' FROM agno."{tname}"'
                                    f" ORDER BY updated_at DESC LIMIT :limit"
                                ),
                                {"limit": limit},
                            ).fetchall()
                        rows.extend(chunk)
                    except Exception:
                        pass
        except Exception as exc:
            logger.warning(f"list_memories error: {exc}")
            return []

    result = []
    for row in rows[:limit]:
        mid, mem_raw, topics_raw, uid, ts = row

        # mem_raw may be a dict (jsonb) or plain string
        if isinstance(mem_raw, dict):
            mem_text = mem_raw.get("memory", str(mem_raw))
        else:
            mem_text = str(mem_raw) if mem_raw else ""

        if isinstance(topics_raw, list):
            topics = [str(t) for t in topics_raw]
        else:
            topics = []

        result.append(
            {
                "id": str(mid) if mid else str(uuid.uuid4()),
                "memory": mem_text,
                "topics": topics,
                "user_id": uid or "",
                "timestamp": ts,
            }
        )
    return result


def clear_memory(
    agent_id: str,
    user_id: str,
    session_id: Optional[str] = None,
) -> int:
    """
    Delete all Agno semantic memories for a user.

    session_id is accepted for API compatibility; Agno doesn't scope memories
    by session, so all memories for the user are deleted either way.

    Returns the number of memories deleted.
    """
    try:
        memory_db = get_memory_db(agent_id)
        memory_manager = MemoryManager(db=memory_db)
        memories = memory_manager.get_user_memories(user_id=user_id) or []
        count = 0
        for mem in memories:
            mid = getattr(mem, "memory_id", None) or getattr(mem, "id", None)
            if mid:
                memory_manager.delete_user_memory(memory_id=mid, user_id=user_id)
                count += 1
        return count
    except Exception as exc:
        logger.warning(
            f"Could not clear memories for agent={agent_id} user={user_id}: {exc}"
        )
        return 0


def delete_all_agent_memory(agent_id: str) -> None:
    """
    Drop Agno memory + session tables for an agent (permanent deletion).

    Called when an agent is permanently deleted.
    """
    from sqlalchemy import text
    from app.db_session import SessionLocal

    short = _short(agent_id)
    with SessionLocal() as db:
        db.execute(text(f'DROP TABLE IF EXISTS agno."memories_{short}" CASCADE'))
        db.execute(text(f'DROP TABLE IF EXISTS agno."sessions_{short}" CASCADE'))
        db.commit()

    logger.info(f"Dropped Agno memory tables for agent_id={agent_id}")
