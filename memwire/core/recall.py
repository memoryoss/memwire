"""Path-based BFS recall with tension detection and knowledge search."""

import json
import math
import time
from collections import deque
from typing import Optional

import numpy as np

from ..config import MemWireConfig
from ..utils.types import GraphNode, GraphEdge, RecallPath, RecallResult, MemoryRecord, KnowledgeChunk
from ..utils.math_ops import cosine_similarity
from ..storage.vector_ops import find_seed_nodes
from .graph import DisplacementGraph


class RecallEngine:
    """Traverses the displacement graph via BFS to find relevant memory paths."""

    def __init__(self, config: MemWireConfig):
        self.config = config

    def recall(
        self,
        query_embedding: np.ndarray,
        graph: DisplacementGraph,
        memories: dict[str, MemoryRecord],
        query_text: str = "",
        qdrant_store=None,
        sparse_indices: Optional[np.ndarray] = None,
        sparse_values: Optional[np.ndarray] = None,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> RecallResult:
        """Find relevant paths through the graph for the given query.

        Also searches knowledge chunks if available.
        """
        # Find seed nodes (entry points)
        seeds = find_seed_nodes(
            query_embedding, graph,
            top_k=self.config.recall_seed_top_k,
            qdrant_store=qdrant_store,
        )
        if not seeds:
            # Still search knowledge even if no memory seeds
            knowledge = self.search_knowledge(
                query_embedding, qdrant_store,
                user_id=user_id, agent_id=agent_id,
                sparse_indices=sparse_indices,
                sparse_values=sparse_values,
            )
            return RecallResult(query=query_text, knowledge=knowledge)

        # BFS from each seed to find paths
        all_paths = []
        for seed_node, seed_score in seeds:
            if seed_score < self.config.recall_min_relevance:
                continue
            paths = self._bfs_paths(
                seed_node, graph, query_embedding,
                max_branch=self.config.recall_bfs_max_branch,
                max_paths=self.config.recall_bfs_max_paths,
            )
            all_paths.extend(paths)

        if not all_paths:
            knowledge = self.search_knowledge(
                query_embedding, qdrant_store,
                user_id=user_id, agent_id=agent_id,
                sparse_indices=sparse_indices,
                sparse_values=sparse_values,
            )
            return RecallResult(query=query_text, knowledge=knowledge)

        # Score and sort paths
        scored_paths = self._score_paths(all_paths, query_embedding, memories)
        scored_paths.sort(key=lambda p: p.score, reverse=True)
        scored_paths = scored_paths[:self.config.recall_max_paths]

        # Attach memories to paths
        for path in scored_paths:
            path.memories = self._collect_memories(path, memories)

        # Detect tensions (conflicting paths)
        supporting, conflicting = self._detect_tensions(scored_paths)

        # Search knowledge chunks
        knowledge = self.search_knowledge(
            query_embedding, qdrant_store,
            user_id=user_id, agent_id=agent_id,
            sparse_indices=sparse_indices,
            sparse_values=sparse_values,
        )

        return RecallResult(
            query=query_text,
            supporting=supporting,
            conflicting=conflicting,
            knowledge=knowledge,
        )

    def search_knowledge(
        self,
        query_embedding: np.ndarray,
        qdrant_store,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        sparse_indices: Optional[np.ndarray] = None,
        sparse_values: Optional[np.ndarray] = None,
        top_k: int = 5,
    ) -> list[KnowledgeChunk]:
        """Search knowledge chunks via Qdrant hybrid search."""
        if qdrant_store is None or user_id is None:
            return []
        if not qdrant_store.has_knowledge(user_id, agent_id):
            return []

        results = qdrant_store.search_knowledge(
            dense_embedding=query_embedding,
            sparse_indices=sparse_indices,
            sparse_values=sparse_values,
            user_id=user_id,
            agent_id=agent_id,
            top_k=top_k,
        )

        chunks = []
        for chunk_id_str, score, payload in results:
            chunks.append(KnowledgeChunk(
                chunk_id=chunk_id_str,
                kb_id=payload.get("kb_id", ""),
                user_id=payload.get("user_id", ""),
                agent_id=payload.get("agent_id") or None,
                content=payload.get("content", ""),
                metadata=json.loads(payload.get("metadata", "{}")),
                score=float(score),
            ))
        return chunks

    def _bfs_paths(
        self,
        seed: GraphNode,
        graph: DisplacementGraph,
        query_embedding: np.ndarray,
        max_branch: int = 5,
        max_paths: int = 200,
    ) -> list[RecallPath]:
        """BFS from seed node, collecting paths up to max_depth.

        Limits branching factor to top-N neighbors by edge weight to prevent
        combinatorial explosion on dense graphs.
        """
        paths = []
        # Queue items: (current_node, path_nodes, path_edges, depth)
        queue: deque[tuple[GraphNode, list[GraphNode], list[GraphEdge], int]] = deque()
        queue.append((seed, [seed], [], 0))
        visited_paths: set[str] = set()

        while queue:
            if len(paths) >= max_paths:
                break

            current, path_nodes, path_edges, depth = queue.popleft()

            if depth > 0:
                path_key = "->".join(n.node_id for n in path_nodes)
                if path_key not in visited_paths:
                    visited_paths.add(path_key)
                    paths.append(RecallPath(
                        nodes=list(path_nodes),
                        edges=list(path_edges),
                    ))

            if depth >= self.config.recall_max_depth:
                continue

            # Expand neighbors — only top-N by edge weight to limit branching
            visited_in_path = {n.node_id for n in path_nodes}
            neighbors = [
                (n, e) for n, e in graph.get_neighbors(current.node_id)
                if n.node_id not in visited_in_path
            ]
            neighbors.sort(key=lambda x: x[1].weight, reverse=True)
            for neighbor, edge in neighbors[:max_branch]:
                queue.append((
                    neighbor,
                    path_nodes + [neighbor],
                    path_edges + [edge],
                    depth + 1,
                ))

        return paths

    def _score_paths(
        self,
        paths: list[RecallPath],
        query_embedding: np.ndarray,
        memories: dict[str, MemoryRecord],
    ) -> list[RecallPath]:
        """Score paths by relevance * coherence * recency."""
        now = time.time()
        for path in paths:
            # Relevance: avg cosine similarity of path nodes to query
            node_sims = [
                cosine_similarity(n.embedding, query_embedding) for n in path.nodes
            ]
            relevance = sum(node_sims) / len(node_sims) if node_sims else 0.0

            # Coherence: average edge weight along the path
            coherence = path.total_weight if path.edges else 0.5

            path.score = relevance * coherence

            # Recency weighting: favor newer memories
            if self.config.recency_weight > 0:
                path_memories = self._collect_memories(path, memories)
                if path_memories:
                    timestamps = [m.timestamp for m in path_memories if m.timestamp > 0]
                    if timestamps:
                        most_recent = max(timestamps)
                        age = now - most_recent
                        recency = math.exp(-age / self.config.recency_halflife)
                        path.score *= (1 - self.config.recency_weight
                                       + self.config.recency_weight * recency)

        return paths

    def _collect_memories(
        self, path: RecallPath, memories: dict[str, MemoryRecord]
    ) -> list[MemoryRecord]:
        """Collect unique memories referenced by path nodes."""
        seen = set()
        result = []
        for node in path.nodes:
            for mid in node.memory_ids:
                if mid not in seen and mid in memories:
                    seen.add(mid)
                    result.append(memories[mid])
        return result

    def _detect_tensions(
        self, paths: list[RecallPath]
    ) -> tuple[list[RecallPath], list[RecallPath]]:
        """Split paths into supporting and conflicting groups.

        Paths conflict when their node embeddings point in sufficiently
        different directions (geometric tension via displacement).
        """
        if len(paths) <= 1:
            return (paths, [])

        supporting = [paths[0]]
        conflicting = []
        conflicting_ids: set[int] = set()

        # Use the top path as reference
        ref_embedding = np.mean(
            [n.embedding for n in paths[0].nodes], axis=0
        )

        for i, path in enumerate(paths[1:], start=1):
            path_embedding = np.mean(
                [n.embedding for n in path.nodes], axis=0
            )
            sim = cosine_similarity(ref_embedding, path_embedding)

            if sim < (1.0 - self.config.tension_threshold):
                conflicting.append(path)
                conflicting_ids.add(i)
            else:
                supporting.append(path)

        return (supporting, conflicting)
