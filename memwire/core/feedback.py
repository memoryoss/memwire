"""Edge-only feedback loop — strengthens/weakens graph edges based on response alignment."""

import numpy as np

from ..config import MemWireConfig
from ..utils.types import RecallResult, RecallPath
from ..utils.math_ops import cosine_similarity
from .graph import DisplacementGraph


class FeedbackProcessor:
    """Compares LLM response to recalled paths and adjusts edge weights only."""

    def __init__(self, config: MemWireConfig):
        self.config = config

    def process(
        self,
        response_embedding: np.ndarray,
        recall_result: RecallResult,
        graph: DisplacementGraph,
    ) -> dict[str, int]:
        """Process feedback: strengthen edges on aligned paths, weaken misaligned ones.

        Returns dict with counts: {"strengthened": N, "weakened": M}
        """
        stats = {"strengthened": 0, "weakened": 0}

        for path in recall_result.supporting:
            alignment = self._path_alignment(response_embedding, path)
            if alignment > self.config.feedback_align_strengthen:
                self._strengthen_path(path, graph, alignment)
                stats["strengthened"] += len(path.edges)
            elif alignment < self.config.feedback_align_weaken:
                self._weaken_path(path, graph)
                stats["weakened"] += len(path.edges)

        for path in recall_result.conflicting:
            alignment = self._path_alignment(response_embedding, path)
            if alignment > self.config.feedback_align_strengthen:
                # Response actually aligned with the "conflicting" path — strengthen it
                self._strengthen_path(path, graph, alignment)
                stats["strengthened"] += len(path.edges)
            else:
                self._weaken_path(path, graph)
                stats["weakened"] += len(path.edges)

        return stats

    def _path_alignment(self, response_embedding: np.ndarray, path: RecallPath) -> float:
        """How well the response aligns with a path (avg cosine sim to path nodes)."""
        if not path.nodes:
            return 0.0
        sims = [
            cosine_similarity(response_embedding, node.embedding)
            for node in path.nodes
        ]
        return float(np.mean(sims))

    def _strengthen_path(
        self, path: RecallPath, graph: DisplacementGraph, alignment: float
    ) -> None:
        """Strengthen all edges along a path, scaled by alignment."""
        amount = self.config.feedback_strengthen_rate * alignment
        for edge in path.edges:
            graph.strengthen_edge(edge.source_id, edge.target_id, amount)

    def _weaken_path(self, path: RecallPath, graph: DisplacementGraph) -> None:
        """Weaken all edges along a path."""
        for edge in path.edges:
            graph.weaken_edge(
                edge.source_id, edge.target_id, self.config.feedback_weaken_rate
            )
