"""Cross-encoder reranker for search quality improvement."""

from ..config import MemWireConfig
from ..utils.types import MemoryRecord


class Reranker:
    """Lazy-loaded cross-encoder reranker using FastEmbed."""

    def __init__(self, config: MemWireConfig):
        self.config = config
        self._model = None

    def _get_model(self):
        if self._model is None:
            from fastembed.rerank.cross_encoder import TextCrossEncoder
            self._model = TextCrossEncoder(self.config.reranker_model_name)
        return self._model

    def rerank(
        self,
        query: str,
        results: list[tuple[MemoryRecord, float]],
        top_k: int = 10,
    ) -> list[tuple[MemoryRecord, float]]:
        """Rerank results using cross-encoder scores.
        """
        if not results:
            return results

        model = self._get_model()
        documents = [mem.content for mem, _ in results]

        # Cross-encoder reranking
        rerank_results = list(model.rerank(query, documents))

        # Map scores back to MemoryRecords
        scored = []
        for rr in rerank_results:
            idx = rr.index
            score = rr.score
            scored.append((results[idx][0], float(score)))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]
