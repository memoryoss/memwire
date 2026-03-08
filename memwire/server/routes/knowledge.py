"""Knowledge base endpoints: add, search, delete."""

from fastapi import APIRouter, Request, HTTPException, Query

from ..schemas import (
    AddKnowledgeRequest, KnowledgeResponse,
    SearchKnowledgeRequest,
)

router = APIRouter(prefix="/v1/knowledge", tags=["knowledge"])


@router.post("", response_model=KnowledgeResponse)
def add_knowledge(body: AddKnowledgeRequest, request: Request):
    memory = request.app.state.memory
    kb_id = memory.add_knowledge(
        body.name,
        [c.model_dump() for c in body.chunks],
        user_id=body.user_id,
        agent_id=body.agent_id,
        app_id=body.app_id,
        workspace_id=body.workspace_id,
    )
    return KnowledgeResponse(kb_id=kb_id)


@router.post("/search")
def search_knowledge(body: SearchKnowledgeRequest, request: Request):
    memory = request.app.state.memory
    chunks = memory.search_knowledge(
        body.query,
        user_id=body.user_id,
        agent_id=body.agent_id,
        app_id=body.app_id,
        workspace_id=body.workspace_id,
        top_k=body.top_k,
    )
    return [
        {"chunk_id": c.chunk_id, "kb_id": c.kb_id, "content": c.content,
         "score": c.score, "metadata": c.metadata}
        for c in chunks
    ]


@router.delete("/{kb_id}")
def delete_knowledge(kb_id: str, user_id: str = Query(...), request: Request = None):
    memory = request.app.state.memory
    # verify ownership
    kbs = memory.db.load_knowledge_bases(user_id)
    if not any(kb["kb_id"] == kb_id for kb in kbs):
        raise HTTPException(status_code=404, detail="Knowledge base not found for user")
    memory.delete_knowledge(kb_id)
    return {"deleted": kb_id}
