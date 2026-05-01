"""Knowledge base endpoints: add, list, search, delete, ingest."""

import os
import shutil
import tempfile
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, Query, UploadFile, File, Form

from ..schemas import (
    AddKnowledgeRequest, KnowledgeResponse,
    SearchKnowledgeRequest, IngestResponse,
    KnowledgeListItem, KnowledgeListResponse,
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


@router.get("", response_model=KnowledgeListResponse)
def list_knowledge(
    request: Request,
    user_id: Optional[str] = Query(None),
    agent_id: Optional[str] = Query(None),
    workspace_id: Optional[str] = Query(None),
    app_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    memory = request.app.state.memory
    items, total = memory.db.list_knowledge_bases(
        user_id=user_id,
        agent_id=agent_id,
        workspace_id=workspace_id,
        app_id=app_id,
        search=search,
        limit=limit,
        offset=offset,
    )
    return KnowledgeListResponse(
        items=[KnowledgeListItem(**i) for i in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/ingest", response_model=IngestResponse)
def ingest_document(
    request: Request,
    file: UploadFile = File(...),
    user_id: str = Form(...),
    name: Optional[str] = Form(None),
    agent_id: Optional[str] = Form(None),
    app_id: Optional[str] = Form(None),
    workspace_id: Optional[str] = Form(None),
    chunk_max_characters: Optional[int] = Form(None),
    chunk_overlap: Optional[int] = Form(None),
):
    """Upload and ingest a document file into a knowledge base."""
    memory = request.app.state.memory

    suffix = os.path.splitext(file.filename or "")[1]
    fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(fd, "wb") as tmp:
            shutil.copyfileobj(file.file, tmp)

        kb_id = memory.ingest(
            tmp_path,
            name=name or file.filename,
            user_id=user_id,
            agent_id=agent_id,
            app_id=app_id,
            workspace_id=workspace_id,
            chunk_max_characters=chunk_max_characters,
            chunk_overlap=chunk_overlap,
        )
    except ImportError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to ingest document: {e}")
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    kbs = memory.db.load_knowledge_bases(user_id, agent_id)
    chunk_count = 0
    for kb in kbs:
        if kb["kb_id"] == kb_id:
            chunk_count = kb.get("chunk_count", 0)
            break

    return IngestResponse(
        kb_id=kb_id,
        name=name or file.filename or "unknown",
        chunks=chunk_count,
    )


@router.post("/search")
def search_knowledge(body: SearchKnowledgeRequest, request: Request):
    memory = request.app.state.memory
    chunks = memory.search_knowledge(
        body.query,
        user_id=body.user_id,
        agent_id=body.agent_id,
        app_id=body.app_id,
        workspace_id=body.workspace_id,
        top_k=body.limit,
    )
    return [
        {"chunk_id": c.chunk_id, "kb_id": c.kb_id, "content": c.content,
         "score": c.score, "metadata": c.metadata}
        for c in chunks
    ]


@router.delete("/{kb_id}")
def delete_knowledge(kb_id: str, user_id: str = Query(...), request: Request = None):
    memory = request.app.state.memory
    kbs = memory.db.load_knowledge_bases(user_id)
    if not any(kb["kb_id"] == kb_id for kb in kbs):
        raise HTTPException(status_code=404, detail="Knowledge base not found for user")
    memory.delete_knowledge(kb_id)
    return {"deleted": kb_id}
