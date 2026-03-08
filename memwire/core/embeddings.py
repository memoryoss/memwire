"""Token-level embedding engine with displacement computation."""

from collections import OrderedDict

import numpy as np

from ..config import MemWireConfig
from ..utils.types import TokenEmbedding
from ..utils.math_ops import displacement_vector, normalize
from ..utils.tokenizer import Tokenizer
from .providers import create_provider


class EmbeddingEngine:
    """Produces sentence and token-level embeddings with displacement vectors."""

    def __init__(self, config: MemWireConfig):
        self.config = config
        self._provider = create_provider(config)
        self.tokenizer = Tokenizer()
        self._cache: OrderedDict[str, np.ndarray] = OrderedDict()
        self._sparse_model = None  # lazy-loaded, FastEmbed only

    def _get_sparse_model(self):
        if self._sparse_model is None:
            from fastembed import SparseTextEmbedding
            self._sparse_model = SparseTextEmbedding(self.config.sparse_model_name)
        return self._sparse_model

    def _cache_put(self, key: str, value: np.ndarray) -> None:
        self._cache[key] = value
        if len(self._cache) > self.config.embedding_cache_maxsize:
            self._cache.popitem(last=False)

    def embed_sentence(self, text: str) -> np.ndarray:
        """Embed a full sentence, returns normalized vector."""
        if text in self._cache:
            return self._cache[text]
        embedding = self._provider.embed([text])[0]
        self._cache_put(text, embedding)
        return embedding

    def embed_tokens(self, text: str) -> list[TokenEmbedding]:
        """Embed each token in isolation and in context, compute displacement."""
        result = self.tokenizer.tokenize(text)
        if not result.tokens:
            return []

        contextual_sentence = self.embed_sentence(text)

        # batch embed uncached tokens
        uncached_tokens = [t for t in result.tokens if t not in self._cache]
        if uncached_tokens:
            embeddings = self._provider.embed(uncached_tokens)
            for token, emb in zip(uncached_tokens, embeddings):
                self._cache_put(token, emb)

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
            embeddings = self._provider.embed(uncached)
            for text, emb in zip(uncached, embeddings):
                self._cache_put(text, emb)
        return [self._cache[t] for t in texts]

    def embed_sparse(self, text: str) -> tuple[np.ndarray, np.ndarray]:
        """Embed text using SPLADE sparse model. Returns (indices, values)."""
        sparse_model = self._get_sparse_model()
        result = list(sparse_model.embed([text]))[0]
        return result.indices, result.values

    def clear_cache(self):
        self._cache.clear()
