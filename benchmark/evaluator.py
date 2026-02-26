"""Scoring: F1, BLEU-1, LLM-as-judge, and result aggregation."""

import os
import re
import string
import statistics
from dataclasses import dataclass, field

from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI

from .config import BenchmarkConfig


# --- Text normalization ---

def normalize_answer(s) -> str:
    """Lowercase, strip articles/punctuation/whitespace."""
    s = str(s).lower()
    # Remove articles
    s = re.sub(r"\b(a|an|the)\b", " ", s)
    # Remove punctuation
    s = s.translate(str.maketrans("", "", string.punctuation))
    # Collapse whitespace
    s = " ".join(s.split())
    return s


def compute_f1(prediction, gold) -> float:
    """Token-level F1 between prediction and gold answer."""
    pred_tokens = normalize_answer(str(prediction)).split()
    gold_tokens = normalize_answer(str(gold)).split()

    if not gold_tokens:
        return 1.0 if not pred_tokens else 0.0
    if not pred_tokens:
        return 0.0

    common = set(pred_tokens) & set(gold_tokens)
    num_common = sum(min(pred_tokens.count(t), gold_tokens.count(t)) for t in common)

    if num_common == 0:
        return 0.0

    precision = num_common / len(pred_tokens)
    recall = num_common / len(gold_tokens)
    return 2 * precision * recall / (precision + recall)


def compute_bleu1(prediction, gold) -> float:
    """Unigram BLEU with brevity penalty."""
    pred_tokens = normalize_answer(str(prediction)).split()
    gold_tokens = normalize_answer(str(gold)).split()

    if not pred_tokens or not gold_tokens:
        return 0.0

    # Unigram precision (clipped counts)
    gold_counts: dict[str, int] = {}
    for t in gold_tokens:
        gold_counts[t] = gold_counts.get(t, 0) + 1

    clipped = 0
    pred_counts: dict[str, int] = {}
    for t in pred_tokens:
        pred_counts[t] = pred_counts.get(t, 0) + 1

    for t, count in pred_counts.items():
        clipped += min(count, gold_counts.get(t, 0))

    precision = clipped / len(pred_tokens)

    # Brevity penalty
    bp = min(1.0, len(pred_tokens) / len(gold_tokens))

    return bp * precision


# --- LLM Judge ---

JUDGE_PROMPT = """You are evaluating whether a predicted answer is correct given a gold-standard answer.

Question: {question}
Gold Answer: {gold}
Predicted Answer: {predicted}

Judge whether the predicted answer is essentially correct. Minor wording differences are OK.
The predicted answer must contain the key information from the gold answer.

Respond with exactly one word: CORRECT or WRONG"""


class LLMJudge:
    """GPT-4o-mini binary judge for answer correctness."""

    def __init__(self, config: BenchmarkConfig):
        self.client = OpenAI()
        self.model = config.judge_model
        self.temperature = config.judge_temperature

    def judge(self, question: str, gold: str, predicted: str) -> bool:
        """Return True if predicted answer is judged correct."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                max_tokens=10,
                messages=[{
                    "role": "user",
                    "content": JUDGE_PROMPT.format(
                        question=question, gold=gold, predicted=predicted,
                    ),
                }],
            )
            verdict = response.choices[0].message.content.strip().upper()
            return "CORRECT" in verdict
        except Exception as e:
            print(f"  Judge error: {e}")
            return False


# --- Result types ---

@dataclass
class QuestionResult:
    question_id: str
    category: int
    question: str
    gold: str
    predicted: str
    f1: float = 0.0
    bleu1: float = 0.0
    judge_correct: bool = False
    recall_ms: float = 0.0
    generation_ms: float = 0.0
    eval_ms: float = 0.0
    total_ms: float = 0.0
    memory_stats: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "question_id": self.question_id,
            "category": self.category,
            "question": self.question,
            "gold": self.gold,
            "predicted": self.predicted,
            "f1": round(self.f1, 4),
            "bleu1": round(self.bleu1, 4),
            "judge_correct": self.judge_correct,
            "recall_ms": round(self.recall_ms, 1),
            "generation_ms": round(self.generation_ms, 1),
            "eval_ms": round(self.eval_ms, 1),
            "total_ms": round(self.total_ms, 1),
            "memory_stats": self.memory_stats,
        }


# --- Aggregation ---

CATEGORY_NAMES = {
    1: "Single-hop",
    2: "Multi-hop",
    3: "Temporal",
    4: "Open-domain",
    5: "Adversarial",
}


def aggregate_results(
    results: list[QuestionResult], baselines: dict[str, float]
) -> dict:
    """Compute per-category and overall metrics + comparison table."""
    if not results:
        return {"error": "No results to aggregate"}

    # Overall metrics
    all_f1 = [r.f1 for r in results]
    all_bleu = [r.bleu1 for r in results]
    all_correct = [r.judge_correct for r in results]
    all_recall_ms = [r.recall_ms for r in results]
    all_gen_ms = [r.generation_ms for r in results]
    all_total_ms = [r.total_ms for r in results]

    overall_accuracy = sum(all_correct) / len(all_correct) * 100
    overall_f1 = statistics.mean(all_f1) * 100
    overall_bleu = statistics.mean(all_bleu) * 100

    # Per-category
    categories_data = {}
    for cat in sorted(set(r.category for r in results)):
        cat_results = [r for r in results if r.category == cat]
        cat_correct = [r.judge_correct for r in cat_results]
        cat_f1 = [r.f1 for r in cat_results]
        cat_bleu = [r.bleu1 for r in cat_results]

        categories_data[cat] = {
            "name": CATEGORY_NAMES.get(cat, f"Category {cat}"),
            "count": len(cat_results),
            "accuracy": round(sum(cat_correct) / len(cat_correct) * 100, 1),
            "f1": round(statistics.mean(cat_f1) * 100, 1),
            "bleu1": round(statistics.mean(cat_bleu) * 100, 1),
        }

    # Latency stats
    def percentile(data, p):
        if not data:
            return 0.0
        sorted_data = sorted(data)
        k = (len(sorted_data) - 1) * p / 100
        f = int(k)
        c = f + 1 if f + 1 < len(sorted_data) else f
        return sorted_data[f] + (k - f) * (sorted_data[c] - sorted_data[f])

    latency = {
        "recall_p50": round(percentile(all_recall_ms, 50), 1),
        "recall_p95": round(percentile(all_recall_ms, 95), 1),
        "recall_mean": round(statistics.mean(all_recall_ms), 1),
        "generation_p50": round(percentile(all_gen_ms, 50), 1),
        "generation_p95": round(percentile(all_gen_ms, 95), 1),
        "generation_mean": round(statistics.mean(all_gen_ms), 1),
        "total_p50": round(percentile(all_total_ms, 50), 1),
        "total_p95": round(percentile(all_total_ms, 95), 1),
        "total_mean": round(statistics.mean(all_total_ms), 1),
    }

    # Comparison table
    comparison = dict(baselines)
    comparison["memwire"] = round(overall_accuracy, 1)

    return {
        "total_questions": len(results),
        "overall": {
            "accuracy": round(overall_accuracy, 1),
            "f1": round(overall_f1, 1),
            "bleu1": round(overall_bleu, 1),
        },
        "categories": categories_data,
        "latency": latency,
        "comparison": comparison,
    }
