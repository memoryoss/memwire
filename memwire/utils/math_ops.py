"""Math operations: cosine similarity, displacement, normalization, serialization."""

import numpy as np


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def displacement_vector(isolated: np.ndarray, contextual: np.ndarray) -> np.ndarray:
    """Compute displacement: how context shifts a token's meaning."""
    return contextual - isolated


def normalize(v: np.ndarray) -> np.ndarray:
    """L2-normalize a vector. Returns zero vector if norm is 0."""
    norm = np.linalg.norm(v)
    if norm == 0:
        return v
    return v / norm


def sigmoid(x: float) -> float:
    """Sigmoid activation, clamped for numerical stability."""
    x = np.clip(x, -500, 500)
    return float(1.0 / (1.0 + np.exp(-x)))


def weighted_average(vectors: list[np.ndarray], weights: list[float]) -> np.ndarray:
    """Compute weighted average of vectors."""
    if not vectors:
        raise ValueError("Cannot average empty vector list")
    total_weight = sum(weights)
    if total_weight == 0:
        return np.mean(vectors, axis=0)
    result = np.zeros_like(vectors[0], dtype=np.float32)
    for v, w in zip(vectors, weights):
        result += v * w
    return result / total_weight


def batch_cosine_similarity(query: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """Compute cosine similarity between query and each row of matrix."""
    query_norm = np.linalg.norm(query)
    if query_norm == 0:
        return np.zeros(matrix.shape[0])
    row_norms = np.linalg.norm(matrix, axis=1)
    row_norms = np.where(row_norms == 0, 1.0, row_norms)
    return np.dot(matrix, query) / (row_norms * query_norm)
