"""Configuration for MemWire memory system."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MemWireConfig:
    """All thresholds, model names, and defaults for the pipeline."""

    # Embedding model
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384

    # FastEmbed / sparse / reranker models
    sparse_model_name: str = "prithivida/Splade_PP_en_v1"
    reranker_model_name: str = "Xenova/ms-marco-MiniLM-L-6-v2"

    # Qdrant storage (required)
    qdrant_url: Optional[str] = None   # e.g. "http://localhost:6333" for local server
    qdrant_api_key: Optional[str] = None  # API key for Qdrant Cloud
    qdrant_path: Optional[str] = None  # local file path for embedded mode, ":memory:" for tests
    qdrant_collection_prefix: str = ""  # prefix for collection names (e.g. "chat_" → "chat_memories")

    # Search quality
    use_hybrid_search: bool = True
    use_reranking: bool = False

    # Graph construction
    displacement_threshold: float = 0.15
    edge_weight_default: float = 0.5
    edge_weight_min: float = 0.01
    edge_weight_max: float = 1.0
    edge_decay_rate: float = 0.02
    edge_reinforce_amount: float = 0.1

    # Node dedup threshold (was entity_merge_similarity)
    node_merge_similarity: float = 0.85

    # Classification
    classification_threshold: float = 0.05
    default_anchors: dict = field(default_factory=lambda: {
        "fact": [
            "This is a factual statement or piece of information",
            "The capital of France is Paris",
            "Water boils at 100 degrees Celsius",
        ],
        "preference": [
            "This is a personal preference or opinion",
            "I prefer dark mode over light mode",
            "I like my coffee black",
        ],
        "instruction": [
            "This is an instruction or directive to follow",
            "Always respond in formal English",
            "Never share my personal information",
        ],
        "event": [
            "This is an event or something that happened",
            "We had a team meeting yesterday",
            "The server crashed last Tuesday",
        ],
        "entity": [
            "This is information about a specific person, place, or organization",
            "John Smith is our project manager",
            "Acme Corp is based in San Francisco",
            "The Tesla Model 3 is an electric vehicle",
        ],
    })

    # Recall
    recall_max_paths: int = 10
    recall_max_depth: int = 4
    recall_min_relevance: float = 0.25
    tension_threshold: float = 0.6
    recency_weight: float = 0.3
    recency_halflife: float = 3600.0
    recall_seed_top_k: int = 5
    recall_bfs_max_branch: int = 5
    recall_bfs_max_paths: int = 200
    # Feedback
    feedback_strengthen_rate: float = 0.1
    feedback_weaken_rate: float = 0.05
    feedback_align_strengthen: float = 0.5
    feedback_align_weaken: float = 0.2

    # Storage
    database_url: Optional[str] = None
    org_id: str = "default"

    # Embedding cache
    embedding_cache_maxsize: int = 10_000

    # Cross-memory edges
    cross_memory_recent_limit: int = 50

    # Threading
    background_threads: int = 2

    def get_database_url(self) -> str:
        """Return database URL, defaulting to SQLite file per org."""
        if self.database_url:
            return self.database_url
        return f"sqlite:///memwire_{self.org_id}.db"
