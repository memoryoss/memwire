"""Token-level embedding engine with displacement computation."""

from collections import OrderedDict

import numpy as np
from fastembed import TextEmbedding, SparseTextEmbedding

from ..config import MemWireConfig
from ..utils.types import TokenEmbedding
from ..utils.math_ops import displacement_vector, normalize
from ..utils.tokenizer import Tokenizer


class EmbeddingEngine:
    """Produces sentence and token-level embeddings with displacement vectors."""

    def __init__(self, config: MemWireConfig):
        self.config = config
        self.model = TextEmbedding(config.model_name)
        self.tokenizer = Tokenizer()
        self._cache: OrderedDict[str, np.ndarray] = OrderedDict()

        # Sparse model (lazy-loaded on first use)
        self._sparse_model = None

    def _get_sparse_model(self) -> SparseTextEmbedding:
        if self._sparse_model is None:
            self._sparse_model = SparseTextEmbedding(self.config.sparse_model_name)
        return self._sparse_model

    def _cache_put(self, key: str, value: np.ndarray) -> None:
        """Insert into cache with LRU eviction."""
        self._cache[key] = value
        if len(self._cache) > self.config.embedding_cache_maxsize:
            self._cache.popitem(last=False)  # evict oldest

    def embed_sentence(self, text: str) -> np.ndarray:
        """Embed a full sentence, returns normalized vector."""
        if text in self._cache:
            return self._cache[text]
        embedding = list(self.model.embed([text]))[0]
        embedding = normalize(np.array(embedding, dtype=np.float32))
        self._cache_put(text, embedding)
        return embedding

    def embed_tokens(self, text: str) -> list[TokenEmbedding]:
        """Embed each token both in isolation and in context, compute displacement."""
        result = self.tokenizer.tokenize(text)
        if not result.tokens:
            return []

        # Get contextual embedding for the full sentence
        contextual_sentence = self.embed_sentence(text)

        # Batch ALL token isolated embeddings in one call
        uncached_tokens = [t for t in result.tokens if t not in self._cache]
        if uncached_tokens:
            embeddings = list(self.model.embed(uncached_tokens))
            for token, emb in zip(uncached_tokens, embeddings):
                self._cache_put(token, normalize(np.array(emb, dtype=np.float32)))

        # Build token embeddings with displacement
        token_embeddings = []
        for i, token in enumerate(result.tokens):
            isolated = self._cache[token]
            weight = 1.0 / (1.0 + abs(i - len(result.tokens) / 2))
            contextual = normalize(
                isolated * (1 - weight) + contextual_sentence * weight
            ).astype(np.float32)
            disp = displacement_vector(isolated, contextual)

            token_embeddings.append(TokenEmbedding(
                token=token,
                position=i,
                isolated=isolated,
                contextual=contextual,
                displacement=disp,
            ))

        return token_embeddings

    def embed_batch(self, texts: list[str]) -> list[np.ndarray]:
        """Embed multiple sentences efficiently."""
        uncached = [t for t in texts if t not in self._cache]
        if uncached:
            embeddings = list(self.model.embed(uncached))
            for text, emb in zip(uncached, embeddings):
                self._cache_put(text, normalize(np.array(emb, dtype=np.float32)))
        return [self._cache[t] for t in texts]

    def embed_sparse(self, text: str) -> tuple[np.ndarray, np.ndarray]:
        """Embed text using SPLADE sparse model. Returns (indices, values)."""
        sparse_model = self._get_sparse_model()
        result = list(sparse_model.embed([text]))[0]
        return result.indices, result.values

    def clear_cache(self):
        """Clear the embedding cache."""
        self._cache.clear()
