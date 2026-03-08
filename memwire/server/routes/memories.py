"""Memory endpoints: add, recall, search, feedback."""

from fastapi import APIRouter, Request

from ..schemas import (
    AddMemoryRequest, MemoryResponse,
    RecallRequest, RecallResponse, PathResponse,
    SearchRequest, SearchResultResponse,
    FeedbackRequest, FeedbackResponse,
)

router = APIRouter(prefix="/v1/memories", tags=["memories"])


def _memory_to_response(record) -> MemoryResponse:
    return MemoryResponse(
        memory_id=record.memory_id,
        user_id=record.user_id,
        content=record.content,
        role=record.role,
        category=record.category,
        strength=record.strength,
        timestamp=record.timestamp,
        node_ids=record.node_ids,
        agent_id=record.agent_id,
    )


def _path_to_response(path) -> PathResponse:
    return PathResponse(
        tokens=[n.token for n in path.nodes],
        score=path.score,
        memories=[_memory_to_response(m) for m in path.memories],
    )


@router.post("", response_model=list[MemoryResponse])
def add_memories(body: AddMemoryRequest, request: Request):
    memory = request.app.state.memory
    records = memory.add(
        user_id=body.user_id,
        messages=[m.model_dump() for m in body.messages],
        agent_id=body.agent_id,
        app_id=body.app_id,
        workspace_id=body.workspace_id,
    )
    return [_memory_to_response(r) for r in records]


@router.post("/recall", response_model=RecallResponse)
def recall_memories(body: RecallRequest, request: Request):
    memory = request.app.state.memory
    result = memory.recall(
        body.query,
        user_id=body.user_id,
        agent_id=body.agent_id,
        app_id=body.app_id,
        workspace_id=body.workspace_id,
    )
    return RecallResponse(
        query=result.query,
        supporting=[_path_to_response(p) for p in result.supporting],
        conflicting=[_path_to_response(p) for p in result.conflicting],
        knowledge=[
            {"chunk_id": k.chunk_id, "kb_id": k.kb_id, "content": k.content,
             "score": k.score, "metadata": k.metadata}
            for k in result.knowledge
        ],
        formatted=result.formatted,
        has_tensions=result.has_tensions,
    )


@router.post("/search", response_model=list[SearchResultResponse])
def search_memories(body: SearchRequest, request: Request):
    memory = request.app.state.memory
    results = memory.search(
        body.query,
        user_id=body.user_id,
        agent_id=body.agent_id,
        app_id=body.app_id,
        workspace_id=body.workspace_id,
        category=body.category,
        top_k=body.top_k,
    )
    return [
        SearchResultResponse(memory=_memory_to_response(rec), score=score)
        for rec, score in results
    ]


@router.post("/feedback", response_model=FeedbackResponse)
def feedback(body: FeedbackRequest, request: Request):
    memory = request.app.state.memory
    stats = memory.feedback(
        body.response,
        user_id=body.user_id,
        agent_id=body.agent_id,
        app_id=body.app_id,
        workspace_id=body.workspace_id,
    )
    return FeedbackResponse(**stats)
