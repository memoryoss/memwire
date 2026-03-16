"""Embedding providers: FastEmbed (local) and OpenAI-compatible (Ollama, OpenAI, etc.)."""

import logging
from abc import ABC, abstractmethod

import numpy as np
import httpx

from ..config import MemWireConfig
from ..utils.math_ops import normalize

logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    """Base interface for embedding providers."""

    @abstractmethod
    def embed(self, texts: list[str]) -> list[np.ndarray]:
        """Embed a batch of texts. Returns list of normalized vectors."""
        ...


class FastEmbedProvider(EmbeddingProvider):
    """Local ONNX embeddings via FastEmbed."""

    def __init__(self, config: MemWireConfig):
        from fastembed import TextEmbedding
        self.model = TextEmbedding(config.model_name)

    def embed(self, texts: list[str]) -> list[np.ndarray]:
        embeddings = list(self.model.embed(texts))
        return [normalize(np.array(e, dtype=np.float32)) for e in embeddings]


class OpenAICompatibleProvider(EmbeddingProvider):
    """Embeddings via any OpenAI-compatible API (Ollama, OpenAI, Together, Mistral, etc.)."""

    def __init__(self, config: MemWireConfig):
        self.model = config.embedding_model
        self.url = config.embedding_api_url.rstrip("/") + "/embeddings"
        headers = {"Content-Type": "application/json"}
        if config.embedding_api_key:
            headers["Authorization"] = f"Bearer {config.embedding_api_key}"
        self._client = httpx.Client(headers=headers, timeout=30.0)

    def embed(self, texts: list[str]) -> list[np.ndarray]:
        resp = self._client.post(self.url, json={"model": self.model, "input": texts})
        resp.raise_for_status()
        data = resp.json()["data"]
        # sort by index to preserve input order
        data.sort(key=lambda x: x["index"])
        return [normalize(np.array(d["embedding"], dtype=np.float32)) for d in data]


def create_provider(config: MemWireConfig) -> EmbeddingProvider:
    """Factory: create the right provider based on config."""
    if config.embedding_provider == "openai-compatible":
        logger.info("Using OpenAI-compatible embeddings: %s @ %s", config.embedding_model, config.embedding_api_url)
        return OpenAICompatibleProvider(config)
    logger.info("Using FastEmbed embeddings: %s", config.model_name)
    return FastEmbedProvider(config)
