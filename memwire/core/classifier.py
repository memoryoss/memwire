"""Anchor-based classification without LLM calls."""

import numpy as np
from typing import Optional

from ..config import MemWireConfig
from ..utils.math_ops import cosine_similarity


class AnchorClassifier:
    """Classifies memories by cosine similarity to anchor embeddings."""

    def __init__(self, config: MemWireConfig):
        self.config = config
        # Normalize to multi-example format: dict[str, list[str]]
        self._anchor_texts: dict[str, list[str]] = {}
        for name, value in config.default_anchors.items():
            if isinstance(value, list):
                self._anchor_texts[name] = list(value)
            else:
                self._anchor_texts[name] = [value]
        self._anchor_embeddings: dict[str, np.ndarray] = {}
        self._initialized = False

    def initialize(self, embed_fn) -> None:
        """Compute anchor embeddings as centroids of multiple examples."""
        for name, texts in self._anchor_texts.items():
            embeddings = [embed_fn(t) for t in texts]
            self._anchor_embeddings[name] = np.mean(embeddings, axis=0)
        self._initialized = True

    def classify(self, embedding: np.ndarray) -> tuple[str, float]:
        """Classify by argmax cosine similarity to anchors.

        Returns (category_name, confidence).
        """
        if not self._initialized or not self._anchor_embeddings:
            return ("unknown", 0.0)

        best_name = "unknown"
        best_sim = -1.0

        for name, anchor_emb in self._anchor_embeddings.items():
            sim = cosine_similarity(embedding, anchor_emb)
            if sim > best_sim:
                best_sim = sim
                best_name = name

        if best_sim < self.config.classification_threshold:
            return ("unknown", best_sim)

        return (best_name, best_sim)

    def add_anchor(self, name: str, text: str, embed_fn) -> None:
        """Add or update a classification anchor (single text for backward compat)."""
        if name in self._anchor_texts:
            self._anchor_texts[name].append(text)
        else:
            self._anchor_texts[name] = [text]
        # Recompute centroid for this anchor
        embeddings = [embed_fn(t) for t in self._anchor_texts[name]]
        self._anchor_embeddings[name] = np.mean(embeddings, axis=0)
        self._initialized = True

    def remove_anchor(self, name: str) -> bool:
        """Remove a classification anchor."""
        removed = False
        if name in self._anchor_texts:
            del self._anchor_texts[name]
            removed = True
        if name in self._anchor_embeddings:
            del self._anchor_embeddings[name]
        return removed

    def get_anchors(self) -> dict[str, list[str]]:
        """Return all anchor name -> texts mappings."""
        return dict(self._anchor_texts)

    def get_top_k(self, embedding: np.ndarray, k: int = 3) -> list[tuple[str, float]]:
        """Return top-k categories with scores."""
        if not self._initialized:
            return []
        scores = []
        for name, anchor_emb in self._anchor_embeddings.items():
            sim = cosine_similarity(embedding, anchor_emb)
            scores.append((name, sim))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:k]
