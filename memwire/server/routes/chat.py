"""Chat proxy: recall → inject context → call LLM → background-persist + feedback."""

import logging
import time

import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from ..schemas import (
    ChatMessage, ChatRequest, ChatResponse, ChatUsage,
    MemoryResponse, PathResponse, RecallResponse,
    ProviderInfo, ProvidersResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/chat", tags=["chat"])


def _path_to_response(path) -> PathResponse:
    return PathResponse(
        tokens=[n.token for n in path.nodes],
        score=path.score,
        memories=[
            MemoryResponse(
                memory_id=m.memory_id,
                user_id=m.user_id,
                content=m.content,
                role=m.role,
                category=m.category,
                strength=m.strength,
                timestamp=m.timestamp,
                node_ids=m.node_ids,
                agent_id=m.agent_id,
            )
            for m in path.memories
        ],
    )


def _recall_to_response(result) -> RecallResponse:
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
        has_conflicts=result.has_conflicts,
    )


@router.get("/providers", response_model=ProvidersResponse)
def chat_providers(request: Request):
    """Return configured LLM providers (currently a single openai-compatible slot)."""
    llm = getattr(request.app.state, "llm", None)
    if llm is None:
        info = ProviderInfo(
            configured=False,
            base_url="",
            default_model="",
            available_models=[],
        )
    else:
        info = ProviderInfo(
            configured=True,
            base_url=llm.config.base_url,
            default_model=llm.config.default_model,
            available_models=llm.config.available_models,
        )
    return ProvidersResponse(providers={"openai": info})


@router.post("", response_model=ChatResponse)
async def chat(body: ChatRequest, request: Request, background_tasks: BackgroundTasks):
    memory = request.app.state.memory
    llm = getattr(request.app.state, "llm", None)
    if llm is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "LLM provider not configured. "
                "Set OPENAI_API_KEY (and optionally OPENAI_BASE_URL, OPENAI_DEFAULT_MODEL)."
            ),
        )
    if not body.messages:
        raise HTTPException(status_code=400, detail="messages must not be empty")

    last_user = next((m for m in reversed(body.messages) if m.role == "user"), None)
    if last_user is None:
        raise HTTPException(
            status_code=400,
            detail="messages must contain at least one message with role='user'",
        )

    # 1. Recall context for the latest user turn
    recall_start = time.perf_counter()
    recall_result = memory.recall(
        last_user.content,
        user_id=body.user_id,
        agent_id=body.agent_id,
        app_id=body.app_id,
        workspace_id=body.workspace_id,
    )
    recall_ms = (time.perf_counter() - recall_start) * 1000.0

    # 2. Build the messages we send upstream
    llm_messages: list[dict] = []
    if recall_result.formatted:
        llm_messages.append({
            "role": "system",
            "content": (
                "You are a helpful assistant. The following memory context was "
                "recalled for this user — use it when relevant:\n\n"
                f"{recall_result.formatted}"
            ),
        })
    for m in body.messages:
        llm_messages.append({"role": m.role, "content": m.content})

    # 3. Call upstream
    llm_start = time.perf_counter()
    try:
        llm_response = await llm.chat(llm_messages, model=body.model)
    except httpx.HTTPStatusError as e:
        detail = e.response.text or str(e)
        status = e.response.status_code
        raise HTTPException(status_code=status, detail=f"LLM call failed: {detail}")
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"LLM unreachable: {e}")

    llm_ms = (time.perf_counter() - llm_start) * 1000.0

    try:
        assistant_content = llm_response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise HTTPException(status_code=502, detail="LLM returned an unexpected response shape.")

    used_model = llm_response.get("model", body.model or llm.config.default_model)
    usage_raw = llm_response.get("usage") or {}
    user_content = last_user.content

    # 4. Background: persist user + assistant turns, then feedback to reinforce edges.
    def _persist():
        try:
            memory.add(
                user_id=body.user_id,
                messages=[
                    {"role": "user", "content": user_content},
                    {"role": "assistant", "content": assistant_content},
                ],
                agent_id=body.agent_id,
                app_id=body.app_id,
                workspace_id=body.workspace_id,
            )
            memory.feedback(
                assistant_content,
                user_id=body.user_id,
                agent_id=body.agent_id,
                app_id=body.app_id,
                workspace_id=body.workspace_id,
            )
        except Exception as exc:
            logger.warning("Background chat persistence failed: %s", exc)

    background_tasks.add_task(_persist)

    return ChatResponse(
        message=ChatMessage(role="assistant", content=assistant_content),
        model=used_model,
        recall=_recall_to_response(recall_result),
        usage=ChatUsage(
            prompt_tokens=int(usage_raw.get("prompt_tokens", 0) or 0),
            completion_tokens=int(usage_raw.get("completion_tokens", 0) or 0),
            total_tokens=int(usage_raw.get("total_tokens", 0) or 0),
        ),
        recall_ms=round(recall_ms, 1),
        llm_ms=round(llm_ms, 1),
    )
