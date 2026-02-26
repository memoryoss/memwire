"""Benchmark configuration."""

import os
from dataclasses import dataclass, field
from pathlib import Path

BENCHMARK_DIR = Path(__file__).parent
DATA_DIR = BENCHMARK_DIR / "data"
RESULTS_DIR = BENCHMARK_DIR / "results"


@dataclass
class BenchmarkConfig:
    data_dir: Path = DATA_DIR
    results_dir: Path = RESULTS_DIR
    dataset_file: str = "locomo10.json"

    # LLM settings
    answer_model: str = "gpt-4o-mini"
    judge_model: str = "gpt-4o-mini"
    answer_temperature: float = 0.3
    judge_temperature: float = 0.1

    # Retrieval
    recall_top_k: int = 10
    search_top_k: int = 10

    # Evaluation
    categories: list[int] = field(default_factory=lambda: [1, 2, 3, 4])
    max_conversations: int | None = None  # None = all 10
    max_questions: int | None = None  # None = all per conversation

    # Baselines (from published papers)
    baselines: dict[str, float] = field(default_factory=lambda: {
        "Mem0": 66.9,
        "Zep": 66.0,
        "LangMem": 30.8,
        "Letta": 74.0,
    })

    # Web dashboard
    web_port: int = 8001

    @property
    def dataset_path(self) -> Path:
        return self.data_dir / self.dataset_file

    @property
    def progress_path(self) -> Path:
        return self.results_dir / "progress.json"

    @property
    def results_path(self) -> Path:
        return self.results_dir / "results.json"
