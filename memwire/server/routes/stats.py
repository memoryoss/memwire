"""Dashboard stats, activity feed, workspace listing, graph viz, auth info."""

import os
from typing import Optional

from fastapi import APIRouter, Query, Request

from ..schemas import (
    DashboardStatsResponse, ActivityResponse, ActivityItem,
    WorkspaceListResponse, WorkspaceItem,
    GraphResponse, GraphNodeOut, GraphEdgeOut,
    AuthInfoResponse,
)

router = APIRouter(prefix="/v1", tags=["stats"])


@router.get("/stats", response_model=DashboardStatsResponse)
def dashboard_stats(
    request: Request,
    org_id: Optional[str] = Query(None),
):
    memory = request.app.state.memory
    return DashboardStatsResponse(**memory.db.dashboard_stats(org_id=org_id))


@router.get("/activity", response_model=ActivityResponse)
def activity_feed(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    org_id: Optional[str] = Query(None),
):
    memory = request.app.state.memory
    items = memory.db.recent_activity(limit=limit, org_id=org_id)
    return ActivityResponse(items=[ActivityItem(**i) for i in items])


@router.get("/workspaces", response_model=WorkspaceListResponse)
def list_workspaces(
    request: Request,
    org_id: Optional[str] = Query(None),
):
    memory = request.app.state.memory
    items = memory.db.list_workspaces(org_id=org_id)
    return WorkspaceListResponse(items=[WorkspaceItem(**i) for i in items])


@router.get("/graph", response_model=GraphResponse)
def graph(
    request: Request,
    user_id: str = Query(..., description="Required — graph is per-user"),
    app_id: Optional[str] = Query(None),
    workspace_id: Optional[str] = Query(None),
    limit: int = Query(300, ge=1, le=2000),
):
    """Return nodes + edges of a user's displacement graph for visualization.

    Pulls from the in-memory DisplacementGraph (lazy-loads from Qdrant + SQL on
    first access). Nodes are sorted by connection count (most-connected first)
    and capped at ``limit``. Edges are filtered to only those between included
    nodes.
    """
    memory = request.app.state.memory
    graph_obj = memory._get_graph(
        user_id, app_id=app_id, workspace_id=workspace_id,
    )

    all_nodes = list(graph_obj.nodes.values())
    node_id_set = {n.node_id for n in all_nodes}

    # Many existing edges are persisted with user_id="" because of the
    # merge_cross_memory_edges path — load all edges and scope by node-set
    # instead of by edge.user_id.
    raw_edges = memory.db.load_edges()
    seen: set[tuple[str, str]] = set()
    all_edges = []
    for e in raw_edges:
        if e.source_id not in node_id_set or e.target_id not in node_id_set:
            continue
        key = (e.source_id, e.target_id) if e.source_id < e.target_id else (e.target_id, e.source_id)
        if key in seen:
            continue
        seen.add(key)
        all_edges.append(e)

    conn_count: dict[str, int] = {}
    for e in all_edges:
        conn_count[e.source_id] = conn_count.get(e.source_id, 0) + 1
        conn_count[e.target_id] = conn_count.get(e.target_id, 0) + 1

    sorted_nodes = sorted(
        all_nodes,
        key=lambda n: conn_count.get(n.node_id, 0),
        reverse=True,
    )
    truncated = len(sorted_nodes) > limit
    top = sorted_nodes[:limit]
    top_ids = {n.node_id for n in top}
    filtered_edges = [
        e for e in all_edges if e.source_id in top_ids and e.target_id in top_ids
    ]

    return GraphResponse(
        nodes=[
            GraphNodeOut(
                node_id=n.node_id,
                token=n.token,
                memory_ids=list(n.memory_ids) if n.memory_ids else [],
                connections=conn_count.get(n.node_id, 0),
            )
            for n in top
        ],
        edges=[
            GraphEdgeOut(
                source_id=e.source_id,
                target_id=e.target_id,
                weight=e.weight,
            )
            for e in filtered_edges
        ],
        total_nodes=len(all_nodes),
        total_edges=len(all_edges),
        truncated=truncated,
    )


@router.get("/auth/info", response_model=AuthInfoResponse)
def auth_info(request: Request):
    """Report how many API keys are configured + the prefix of the caller's key."""
    raw = os.getenv("MEMWIRE_API_KEYS", "")
    keys = [k.strip() for k in raw.split(",") if k.strip()]

    current = request.headers.get("X-API-Key", "") or ""
    prefix = current[:8] if current else None

    return AuthInfoResponse(
        configured=len(keys) > 0,
        configured_count=len(keys),
        current_key_prefix=prefix,
    )
