"""Memory Router — /v1/memory/*"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from app.schemas.memory_schemas import (
    StoreMemoryRequest,
    StoreMemoryResponse,
    MemoryHistoryResponse,
    MemoryListResponse,
    MemoryTurn,
    MemorySearchRequest,
    MemorySearchResponse,
    MemorySearchResult,
    ClearMemoryRequest,
    ClearMemoryResponse,
)
from app.services.memory_service import (
    store_memory,
    get_history,
    list_memories,
    search_memories,
    clear_memory,
)
from app.utils.api_keys import require_api_key

router = APIRouter(prefix="/memory")


@router.post("/store", response_model=StoreMemoryResponse)
async def store(
    req: StoreMemoryRequest,
    _: dict = Depends(require_api_key),
):
    """Store a conversation turn (user message + assistant response)."""
    memory_id = await store_memory(
        agent_id=req.agent_id,
        user_id=req.user_id,
        user_message=req.user_message,
        assistant_message=req.assistant_message,
        session_id=req.session_id,
        metadata=req.metadata,
    )
    return StoreMemoryResponse(success=True, memory_id=memory_id)


@router.get("/history", response_model=MemoryHistoryResponse)
async def history(
    agent_id: str = Query(...),
    user_id: str = Query(...),
    limit: int = Query(20, ge=1, le=100),
    session_id: Optional[str] = Query(None),
    _: dict = Depends(require_api_key),
):
    """Retrieve recent conversation history for a user."""
    memories = get_history(
        agent_id=agent_id,
        user_id=user_id,
        limit=limit,
        session_id=session_id,
    )
    memory_models = [
        MemoryTurn(
            id=m["id"],
            memory=m["memory"],
            topics=m.get("topics") or [],
            user_id=m["user_id"],
            timestamp=m.get("timestamp"),
        )
        for m in memories
    ]
    return MemoryHistoryResponse(
        agent_id=agent_id,
        user_id=user_id,
        memories=memory_models,
        total=len(memory_models),
    )


@router.get("/list", response_model=MemoryListResponse)
async def list_all(
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    limit: int = Query(100, ge=1, le=500),
    _: dict = Depends(require_api_key),
):
    """List memories. Optionally filter by agent_id and/or user_id. Returns all if no filter."""
    memories = list_memories(agent_id=agent_id, user_id=user_id, limit=limit)
    items = [
        MemoryTurn(
            id=m["id"],
            memory=m["memory"],
            topics=m.get("topics") or [],
            user_id=m["user_id"],
            timestamp=m.get("timestamp"),
        )
        for m in memories
    ]
    return MemoryListResponse(memories=items, total=len(items))


@router.get("/retrieve", response_model=MemoryListResponse)
async def retrieve(
    agent_id: str = Query(..., description="Agent ID"),
    user_id: Optional[str] = Query(None, description="Filter by user ID (optional)"),
    limit: int = Query(50, ge=1, le=200),
    _: dict = Depends(require_api_key),
):
    """Retrieve memories for an agent. Optionally filter by user_id."""
    memories = list_memories(agent_id=agent_id, user_id=user_id, limit=limit)
    items = [
        MemoryTurn(
            id=m["id"],
            memory=m["memory"],
            topics=m.get("topics") or [],
            user_id=m["user_id"],
            timestamp=m.get("timestamp"),
        )
        for m in memories
    ]
    return MemoryListResponse(memories=items, total=len(items))


@router.post("/search", response_model=MemorySearchResponse)
async def search(
    req: MemorySearchRequest,
    _: dict = Depends(require_api_key),
):
    """Semantic search over Agno memories using MemoryManager."""
    results = search_memories(
        agent_id=req.agent_id,
        query=req.query,
        user_id=req.user_id,
        limit=req.limit,
    )
    return MemorySearchResponse(
        results=[
            MemorySearchResult(
                id=r["id"],
                memory=r["memory"],
                topics=r.get("topics") or [],
                user_id=r["user_id"],
                timestamp=r.get("timestamp"),
            )
            for r in results
        ],
        total=len(results),
    )


@router.delete("/clear", response_model=ClearMemoryResponse)
async def clear(
    req: ClearMemoryRequest,
    _: dict = Depends(require_api_key),
):
    """Clear all memory for a user (optionally scoped to a session)."""
    deleted = clear_memory(
        agent_id=req.agent_id,
        user_id=req.user_id,
        session_id=req.session_id,
    )
    return ClearMemoryResponse(
        success=True,
        deleted_count=deleted,
        message=f"Cleared {deleted} memory turns.",
    )
