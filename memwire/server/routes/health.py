"""Health and stats endpoints."""

from fastapi import APIRouter, Request

from ..schemas import HealthResponse, StatsRequest, StatsResponse, AddAnchorRequest

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health():
    from memwire import __version__
    return HealthResponse(status="ok", version=__version__)


@router.post("/v1/stats", response_model=StatsResponse)
def stats(body: StatsRequest, request: Request):
    memory = request.app.state.memory
    result = memory.get_stats(
        user_id=body.user_id,
        agent_id=body.agent_id,
        app_id=body.app_id,
        workspace_id=body.workspace_id,
    )
    return StatsResponse(**result)


@router.post("/v1/anchors")
def add_anchor(body: AddAnchorRequest, request: Request):
    memory = request.app.state.memory
    memory.add_anchor(
        body.name,
        body.text,
        user_id=body.user_id,
        app_id=body.app_id,
        workspace_id=body.workspace_id,
    )
    return {"status": "ok", "anchor": body.name}
