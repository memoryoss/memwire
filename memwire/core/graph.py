"""Displacement-based graph construction."""

import threading
import uuid
from typing import Optional

import numpy as np

from ..config import MemWireConfig
from ..utils.types import GraphNode, GraphEdge, TokenEmbedding
from ..utils.math_ops import cosine_similarity, batch_cosine_similarity, normalize


class DisplacementGraph:
    """Graph where edges are formed by displacement similarity between tokens."""

    def __init__(self, config: MemWireConfig, qdrant_store=None):
        self.config = config
        self.qdrant_store = qdrant_store
        self.nodes: dict[str, GraphNode] = {}
        self.edges: dict[tuple[str, str], GraphEdge] = {}
        self._adjacency: dict[str, dict[str, tuple[str, str]]] = {}
        self._dirty_edges: set[tuple[str, str]] = set()
        self._dirty_lock = threading.Lock()

    def build_from_tokens(
        self,
        token_embeddings: list[TokenEmbedding],
        memory_id: str,
        user_id: str = "",
        app_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ) -> list[str]:
        """Build graph nodes/edges from token embeddings. Returns created node IDs."""
        if not token_embeddings:
            return []

        node_ids = []
        for te in token_embeddings:
            node = self._find_or_create_node(
                te, memory_id,
                user_id=user_id, app_id=app_id, workspace_id=workspace_id,
            )
            node_ids.append(node.node_id)

        # Connect nodes whose displacement vectors are similar
        for i, te_a in enumerate(token_embeddings):
            for j, te_b in enumerate(token_embeddings):
                if i >= j:
                    continue
                disp_sim = cosine_similarity(te_a.displacement, te_b.displacement)
                if disp_sim > self.config.displacement_threshold:
                    self._add_edge(node_ids[i], node_ids[j], disp_sim, user_id=user_id)

        return node_ids

    def _find_or_create_node(
        self,
        te: TokenEmbedding,
        memory_id: str,
        user_id: str = "",
        app_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ) -> GraphNode:
        """Find existing node for this token or create a new one."""
        # Qdrant-accelerated dedup for large graphs
        if self.qdrant_store is not None and len(self.nodes) > 50:
            results = self.qdrant_store.search_nodes(
                te.contextual, top_k=1,
                user_id=user_id or None, app_id=app_id, workspace_id=workspace_id,
            )
            if results:
                node_id_str, score = results[0]
                if score > self.config.node_merge_similarity and node_id_str in self.nodes:
                    node = self.nodes[node_id_str]
                    if memory_id not in node.memory_ids:
                        node.memory_ids.append(memory_id)
                    return node
        # Vectorized approach for larger graphs
        elif len(self.nodes) > 50:
            node_list = list(self.nodes.values())
            matrix = np.stack([n.embedding for n in node_list])
            sims = batch_cosine_similarity(te.contextual, matrix)
            best_idx = int(np.argmax(sims))
            if sims[best_idx] > self.config.node_merge_similarity:
                node = node_list[best_idx]
                if memory_id not in node.memory_ids:
                    node.memory_ids.append(memory_id)
                return node
        else:
            # Linear scan for small graphs
            for node in self.nodes.values():
                sim = cosine_similarity(node.embedding, te.contextual)
                if sim > self.config.node_merge_similarity:
                    if memory_id not in node.memory_ids:
                        node.memory_ids.append(memory_id)
                    return node

        node_id = f"node_{uuid.uuid4().hex[:12]}"
        node = GraphNode(
            node_id=node_id,
            token=te.token,
            embedding=te.contextual,
            memory_ids=[memory_id],
            user_id=user_id,
            app_id=app_id,
            workspace_id=workspace_id,
        )
        self.nodes[node_id] = node
        self._adjacency[node_id] = {}
        return node

    def add_node(self, node: GraphNode) -> None:
        """Add a pre-built node to the graph."""
        self.nodes[node.node_id] = node
        if node.node_id not in self._adjacency:
            self._adjacency[node.node_id] = {}

    def _add_edge(self, source_id: str, target_id: str, disp_sim: float, user_id: str = "") -> GraphEdge:
        """Add or update an edge between two nodes."""
        key = (min(source_id, target_id), max(source_id, target_id))
        if key in self.edges:
            edge = self.edges[key]
            edge.weight = min(edge.weight + self.config.edge_reinforce_amount, self.config.edge_weight_max)
            edge.displacement_sim = max(edge.displacement_sim, disp_sim)
            with self._dirty_lock:
                self._dirty_edges.add(key)
            return edge

        edge = GraphEdge(
            source_id=key[0],
            target_id=key[1],
            weight=self.config.edge_weight_default,
            displacement_sim=disp_sim,
            user_id=user_id,
        )
        self.edges[key] = edge
        self._adjacency.setdefault(key[0], {})[key[1]] = key
        self._adjacency.setdefault(key[1], {})[key[0]] = key
        with self._dirty_lock:
            self._dirty_edges.add(key)
        return edge

    def add_edge(self, source_id: str, target_id: str, weight: float, disp_sim: float = 0.0) -> Optional[GraphEdge]:
        """Public edge addition with explicit weight."""
        if source_id not in self.nodes or target_id not in self.nodes:
            return None
        key = (min(source_id, target_id), max(source_id, target_id))
        edge = GraphEdge(source_id=key[0], target_id=key[1], weight=weight, displacement_sim=disp_sim)
        self.edges[key] = edge
        self._adjacency.setdefault(key[0], {})[key[1]] = key
        self._adjacency.setdefault(key[1], {})[key[0]] = key
        with self._dirty_lock:
            self._dirty_edges.add(key)
        return edge

    def pop_dirty_edges(self) -> list[GraphEdge]:
        """Atomically return and clear all dirty edges for persistence."""
        with self._dirty_lock:
            snapshot = self._dirty_edges
            self._dirty_edges = set()
        return [self.edges[k] for k in snapshot if k in self.edges]

    def get_neighbors(self, node_id: str) -> list[tuple[GraphNode, GraphEdge]]:
        """Get all neighbors of a node with their connecting edges."""
        if node_id not in self._adjacency:
            return []
        neighbors = []
        for neighbor_id, edge_key in self._adjacency[node_id].items():
            if neighbor_id in self.nodes and edge_key in self.edges:
                neighbors.append((self.nodes[neighbor_id], self.edges[edge_key]))
        return neighbors

    def merge_cross_memory_edges(self, node_ids_a: list[str], node_ids_b: list[str]) -> int:
        """Create edges between nodes from different memories if embeddings are similar.

        Uses batch cosine similarity for O(A*B) comparisons in one matrix op.
        """
        # Filter to valid, distinct nodes
        nodes_a = [self.nodes[nid] for nid in node_ids_a if nid in self.nodes]
        nodes_b = [self.nodes[nid] for nid in node_ids_b if nid in self.nodes]
        if not nodes_a or not nodes_b:
            return 0

        # Batch cosine similarity: matrix_a (A, D) @ matrix_b.T (D, B) → (A, B)
        emb_a = normalize(np.stack([n.embedding for n in nodes_a]))
        emb_b = normalize(np.stack([n.embedding for n in nodes_b]))
        sim_matrix = emb_a @ emb_b.T  # (A, B)

        threshold = self.config.displacement_threshold
        created = 0

        # Find pairs above threshold
        above = np.argwhere(sim_matrix > threshold)
        for idx_a, idx_b in above:
            nid_a = nodes_a[idx_a].node_id
            nid_b = nodes_b[idx_b].node_id
            if nid_a == nid_b:
                continue
            key = (min(nid_a, nid_b), max(nid_a, nid_b))
            if key in self.edges:
                continue
            self._add_edge(nid_a, nid_b, float(sim_matrix[idx_a, idx_b]))
            created += 1

        return created

    def strengthen_edge(self, source_id: str, target_id: str, amount: float) -> None:
        """Increase edge weight."""
        key = (min(source_id, target_id), max(source_id, target_id))
        if key in self.edges:
            self.edges[key].weight = min(
                self.edges[key].weight + amount, self.config.edge_weight_max
            )
            with self._dirty_lock:
                self._dirty_edges.add(key)

    def weaken_edge(self, source_id: str, target_id: str, amount: float) -> None:
        """Decrease edge weight, remove if below minimum."""
        key = (min(source_id, target_id), max(source_id, target_id))
        if key in self.edges:
            self.edges[key].weight -= amount
            if self.edges[key].weight < self.config.edge_weight_min:
                self._remove_edge(key)
            else:
                with self._dirty_lock:
                    self._dirty_edges.add(key)

    def decay_all(self) -> int:
        """Apply decay to all edges. Returns count of removed edges."""
        to_remove = []
        for key, edge in self.edges.items():
            edge.weight -= self.config.edge_decay_rate
            if edge.weight < self.config.edge_weight_min:
                to_remove.append(key)
        for key in to_remove:
            self._remove_edge(key)
        return len(to_remove)

    def _remove_edge(self, key: tuple[str, str]) -> None:
        """Remove an edge and its adjacency entries."""
        if key in self.edges:
            del self.edges[key]
        src, tgt = key
        if src in self._adjacency and tgt in self._adjacency[src]:
            del self._adjacency[src][tgt]
        if tgt in self._adjacency and src in self._adjacency[tgt]:
            del self._adjacency[tgt][src]
