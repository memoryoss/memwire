"""Vector similarity search and graph rebuild from database."""

import json

import numpy as np

from ..config import MemWireConfig
from ..utils.types import MemoryRecord, GraphNode, GraphEdge
from ..utils.math_ops import batch_cosine_similarity
from ..core.graph import DisplacementGraph


def find_similar_memories(
    query_embedding: np.ndarray,
    memories: list[MemoryRecord],
    top_k: int = 10,
    min_similarity: float = 0.0,
    category: str | None = None,
    qdrant_store=None,
    sparse_indices: np.ndarray | None = None,
    sparse_values: np.ndarray | None = None,
    user_id: str | None = None,
    agent_id: str | None = None,
    memory_dict: dict[str, MemoryRecord] | None = None,
    workspace_id: str | None = None,
    app_id: str | None = None,
) -> list[tuple[MemoryRecord, float]]:
    """Find memories most similar to query embedding via Qdrant hybrid search.

    Returns list of (memory, similarity_score) sorted by score descending.
    """
    if qdrant_store is None:
        return []

    results_raw = qdrant_store.hybrid_search(
        dense_embedding=query_embedding,
        sparse_indices=sparse_indices,
        sparse_values=sparse_values,
        user_id=user_id,
        agent_id=agent_id,
        category=category,
        top_k=top_k,
        workspace_id=workspace_id,
        app_id=app_id,
    )

    # Resolve memory IDs from in-memory dict or payload
    results = []
    for memory_id_str, score, payload in results_raw:
        if memory_dict and memory_id_str in memory_dict:
            mem = memory_dict[memory_id_str]
        else:
            # Reconstruct from payload
            mem = MemoryRecord(
                memory_id=memory_id_str,
                user_id=payload.get("user_id", ""),
                content=payload.get("content", ""),
                role=payload.get("role", "user"),
                embedding=query_embedding,  # placeholder
                category=payload.get("category") or None,
                strength=payload.get("strength", 1.0),
                timestamp=payload.get("timestamp", 0.0),
                node_ids=json.loads(payload.get("node_ids", "[]")),
                agent_id=payload.get("agent_id") or None,
                access_count=payload.get("access_count", 0),
                org_id=payload.get("org_id", ""),
                workspace_id=payload.get("workspace_id") or None,
                app_id=payload.get("app_id") or None,
            )

        if score >= min_similarity:
            results.append((mem, float(score)))

    return results[:top_k]


def find_seed_nodes(
    query_embedding: np.ndarray,
    graph: DisplacementGraph,
    top_k: int = 5,
    qdrant_store=None,
    user_id: str | None = None,
    app_id: str | None = None,
    workspace_id: str | None = None,
) -> list[tuple[GraphNode, float]]:
    """Find graph nodes most similar to query embedding (entry points for BFS).

    Uses Qdrant dense search and maps results back to in-memory graph nodes.
    """
    if not graph.nodes:
        return []

    if qdrant_store is not None:
        results_raw = qdrant_store.search_nodes(
            query_embedding, top_k=top_k,
            user_id=user_id, app_id=app_id, workspace_id=workspace_id,
        )
        results = []
        for node_id_str, score in results_raw:
            if node_id_str in graph.nodes:
                results.append((graph.nodes[node_id_str], float(score)))
        # If Qdrant returned fewer results than needed, supplement from numpy
        if len(results) < top_k:
            found_ids = {r[0].node_id for r in results}
            remaining_nodes = [n for n in graph.nodes.values() if n.node_id not in found_ids]
            if remaining_nodes:
                matrix = np.stack([n.embedding for n in remaining_nodes])
                scores = batch_cosine_similarity(query_embedding, matrix)
                extras = [(node, float(score)) for node, score in zip(remaining_nodes, scores)]
                extras.sort(key=lambda x: x[1], reverse=True)
                results.extend(extras[:top_k - len(results)])
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    # Fallback for when qdrant_store not yet available (shouldn't happen in v2)
    nodes = list(graph.nodes.values())
    matrix = np.stack([n.embedding for n in nodes])
    scores = batch_cosine_similarity(query_embedding, matrix)
    results = [(node, float(score)) for node, score in zip(nodes, scores)]
    results.sort(key=lambda x: x[1], reverse=True)
    return results[:top_k]


def rebuild_graph_from_db(
    nodes: list[GraphNode],
    edges: list[GraphEdge],
    config: MemWireConfig,
) -> DisplacementGraph:
    """Rebuild an in-memory graph from persisted nodes and edges."""
    graph = DisplacementGraph(config)

    for node in nodes:
        graph.add_node(node)

    for edge in edges:
        if edge.source_id in graph.nodes and edge.target_id in graph.nodes:
            graph.add_edge(
                edge.source_id, edge.target_id,
                weight=edge.weight,
                disp_sim=edge.displacement_sim,
            )

    return graph
