"""Core benchmark pipeline: ingest conversations → query → generate → evaluate."""

import json
import os
import sys
import io
import logging
import shutil
import tempfile
import time
from typing import Callable

from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI

from .config import BenchmarkConfig
from .utils import (
    load_locomo,
    parse_conversation_sessions,
    parse_qa_questions,
    turns_to_chunks,
    format_session_date,
    Timer,
)
from .evaluator import (
    LLMJudge,
    QuestionResult,
    compute_f1,
    compute_bleu1,
    aggregate_results,
)

ANSWER_SYSTEM_PROMPT = (
    "You are answering questions about past conversations using retrieved memory context. "
    "Answer based ONLY on the provided context. Be brief and direct. "
    "If the context doesn't contain enough information, say 'I don't know'."
)


class BenchmarkRunner:
    """Run LOCOMO benchmark against memwire."""

    def __init__(
        self,
        config: BenchmarkConfig | None = None,
        progress_callback: Callable | None = None,
    ):
        self.config = config or BenchmarkConfig()
        self.config.results_dir.mkdir(parents=True, exist_ok=True)
        self.config.data_dir.mkdir(parents=True, exist_ok=True)
        self.progress_callback = progress_callback
        self.openai_client = OpenAI()
        self.judge = LLMJudge(self.config)
        self._completed_ids: set[str] = set()
        self._all_results: list[QuestionResult] = []
        self._load_progress()

    def _load_progress(self):
        """Load progress from previous run for resumability."""
        if self.config.progress_path.exists():
            try:
                data = json.loads(self.config.progress_path.read_text())
                self._completed_ids = set(data.get("completed_ids", []))
                self._all_results = [
                    QuestionResult(**r) for r in data.get("results", [])
                ]
                print(f"Resuming: {len(self._completed_ids)} questions already done")
            except Exception:
                self._completed_ids = set()
                self._all_results = []

    def _save_progress(self):
        """Save progress for crash recovery."""
        data = {
            "completed_ids": list(self._completed_ids),
            "results": [r.to_dict() for r in self._all_results],
        }
        self.config.progress_path.write_text(json.dumps(data, indent=2))

    def _emit_progress(self, **kwargs):
        """Send progress update to callback if registered."""
        if self.progress_callback:
            self.progress_callback(kwargs)

    def ingest_conversation(self, conv_idx: int, conversation: dict):
        """Create a fresh MemWire instance and ingest all sessions.

        Uses full graph building (our differentiator) with synchronous
        persistence and tuned cross-memory limit for fast bulk ingestion.

        Returns (memory_instance, stats_dict).
        """
        # Suppress model loading noise
        _stderr = sys.stderr
        sys.stderr = io.StringIO()
        _log_level = logging.root.level
        logging.disable(logging.WARNING)

        try:
            from memwire import MemWire, MemWireConfig

            # Fresh instance per conversation using localhost Qdrant + temp SQLite
            tmp_dir = tempfile.mkdtemp(prefix=f"locomo_conv{conv_idx}_")
            cfg = MemWireConfig(
                user_id=f"locomo_conv{conv_idx}",
                qdrant_url="http://localhost:6333",
                database_url=f"sqlite:///{tmp_dir}/meta.db",
                qdrant_collection_prefix=f"bench{conv_idx}_",
            )
            memory = MemWire(user_id=cfg.user_id, config=cfg)
        finally:
            sys.stderr = _stderr
            logging.disable(logging.NOTSET)
            logging.root.setLevel(_log_level)

        # Make persistence synchronous during ingestion to avoid
        # Qdrant in-memory race conditions (concurrent bg writes + reads)
        memory._submit_bg = lambda fn, *args: fn(*args)

        sessions = parse_conversation_sessions(conversation)
        total_memories = 0

        for session in sessions:
            session_date = format_session_date(session["date_time"])
            chunks = turns_to_chunks(
                session["turns"],
                session_date=session_date,
                chunk_size=5,
                stride=3,
            )
            if not chunks:
                continue

            session_ts = session["timestamp"]
            records = memory.add(chunks)

            # Override timestamps with LOCOMO session dates
            for record in records:
                record.timestamp = session_ts

            total_memories += len(records)

        stats = memory.get_stats()
        stats["total_memories_ingested"] = total_memories
        memory._tmp_dir = tmp_dir  # stash for cleanup
        return memory, stats

    def generate_answer(
        self, memory, question: str
    ) -> tuple[str, str, float, float]:
        """Recall context and generate answer via LLM.

        Returns (answer, context, recall_ms, generation_ms).
        """
        with Timer() as recall_timer:
            context_parts = []
            seen = set()

            # Graph-based recall (BFS through displacement graph)
            recall_result = memory.recall(question)
            if recall_result.formatted:
                context_parts.append(recall_result.formatted)
                for line in recall_result.formatted.split("\n"):
                    text = line.strip().lstrip("- ")
                    if text:
                        seen.add(text)

            # Also do direct vector search for coverage
            search_results = memory.search(question, top_k=self.config.search_top_k)
            for record, score in search_results:
                if record.content not in seen:
                    seen.add(record.content)
                    context_parts.append(f"- {record.content}")

        context = "\n".join(context_parts) if context_parts else "No relevant memories found."

        # Generate answer
        with Timer() as gen_timer:
            try:
                response = self.openai_client.chat.completions.create(
                    model=self.config.answer_model,
                    temperature=self.config.answer_temperature,
                    max_tokens=200,
                    messages=[
                        {"role": "system", "content": ANSWER_SYSTEM_PROMPT},
                        {"role": "user", "content": (
                            f"Memory context:\n{context}\n\n"
                            f"Question: {question}\n\n"
                            "Answer briefly:"
                        )},
                    ],
                )
                answer = response.choices[0].message.content.strip()
            except Exception as e:
                answer = f"Error: {e}"

        return answer, context, recall_timer.elapsed_ms, gen_timer.elapsed_ms

    def run(self) -> dict:
        """Run the full LOCOMO benchmark. Returns aggregated results."""
        conversations = load_locomo(self.config)

        if self.config.max_conversations:
            conversations = conversations[: self.config.max_conversations]

        # Count total questions for progress
        total_questions = 0
        conv_questions = []
        for conv in conversations:
            qa_list = conv.get("qa", conv.get("QA", []))
            questions = parse_qa_questions(qa_list, self.config.categories)
            if self.config.max_questions:
                questions = questions[: self.config.max_questions]
            conv_questions.append(questions)
            total_questions += len(questions)

        done_count = len(self._completed_ids)
        print(f"\nLOCOMO Benchmark: {len(conversations)} conversations, "
              f"{total_questions} questions (cats {self.config.categories})")
        if done_count:
            print(f"  Resuming from {done_count}/{total_questions}")

        self._emit_progress(
            stage="start",
            total_conversations=len(conversations),
            total_questions=total_questions,
            done=done_count,
        )

        for conv_idx, (conversation, questions) in enumerate(
            zip(conversations, conv_questions)
        ):
            conv_id = conversation.get("sample_id", f"conv_{conv_idx}")
            remaining = [q for q in questions if q["question_id"] not in self._completed_ids]

            if not remaining:
                print(f"\n[Conv {conv_idx + 1}/{len(conversations)}] {conv_id} — skipped (done)")
                continue

            print(f"\n[Conv {conv_idx + 1}/{len(conversations)}] {conv_id} — "
                  f"{len(remaining)} questions")

            # Ingest conversation
            self._emit_progress(
                stage="ingesting",
                conversation=conv_idx + 1,
                conv_id=conv_id,
            )

            with Timer() as ingest_timer:
                memory, mem_stats = self.ingest_conversation(conv_idx, conversation)

            ingest_sec = ingest_timer.elapsed_ms / 1000
            print(f"  Ingested: {mem_stats['total_memories_ingested']} memories, "
                  f"{mem_stats['nodes']} nodes, "
                  f"{mem_stats['edges']} edges in {ingest_sec:.1f}s")

            self._emit_progress(
                stage="ingested",
                conversation=conv_idx + 1,
                conv_id=conv_id,
                memories=mem_stats["total_memories_ingested"],
                nodes=mem_stats.get("nodes", 0),
                edges=mem_stats.get("edges", 0),
                ingest_ms=ingest_timer.elapsed_ms,
            )

            # Process each question
            for q_idx, qa in enumerate(remaining):
                qid = qa["question_id"]
                question = qa["question"]
                gold = qa["answer"]
                category = qa["category"]

                self._emit_progress(
                    stage="question",
                    conversation=conv_idx + 1,
                    question_num=done_count + 1,
                    total_questions=total_questions,
                    category=category,
                    question_text=question[:80],
                )

                with Timer() as total_timer:
                    # Generate
                    answer, context, recall_ms, gen_ms = self.generate_answer(
                        memory, question
                    )

                    # Evaluate
                    with Timer() as eval_timer:
                        f1 = compute_f1(answer, gold)
                        bleu1 = compute_bleu1(answer, gold)
                        judge_ok = self.judge.judge(question, gold, answer)

                result = QuestionResult(
                    question_id=qid,
                    category=category,
                    question=question,
                    gold=gold,
                    predicted=answer,
                    f1=f1,
                    bleu1=bleu1,
                    judge_correct=judge_ok,
                    recall_ms=recall_ms,
                    generation_ms=gen_ms,
                    eval_ms=eval_timer.elapsed_ms,
                    total_ms=total_timer.elapsed_ms,
                    memory_stats=mem_stats,
                )

                self._all_results.append(result)
                self._completed_ids.add(qid)
                done_count += 1

                verdict = "OK" if judge_ok else "WRONG"
                print(f"  [{done_count}/{total_questions}] Cat{category} {verdict} "
                      f"F1={f1:.2f} recall={recall_ms:.0f}ms | {question[:55]}...")

                self._emit_progress(
                    stage="result",
                    done=done_count,
                    total_questions=total_questions,
                    result=result.to_dict(),
                )

                # Save progress every 10 questions
                if done_count % 10 == 0:
                    self._save_progress()

            # Cleanup: close memory, delete Qdrant collections, remove temp SQLite
            try:
                memory.close()
            except Exception:
                pass
            try:
                # Delete benchmark collections from Qdrant server
                from qdrant_client import QdrantClient
                cleanup_client = QdrantClient(url="http://localhost:6333")
                prefix = f"bench{conv_idx}_"
                for suffix in ["memories", "graph_nodes", "knowledge_chunks"]:
                    try:
                        cleanup_client.delete_collection(f"{prefix}{suffix}")
                    except Exception:
                        pass
                cleanup_client.close()
            except Exception:
                pass
            try:
                if hasattr(memory, '_tmp_dir') and os.path.isdir(memory._tmp_dir):
                    shutil.rmtree(memory._tmp_dir)
            except Exception:
                pass

        # Final aggregation
        self._save_progress()
        aggregated = aggregate_results(self._all_results, self.config.baselines)
        aggregated["individual_results"] = [r.to_dict() for r in self._all_results]

        # Save final results
        self.config.results_path.write_text(json.dumps(aggregated, indent=2))

        # Print summary
        print("\n" + "=" * 60)
        print("LOCOMO BENCHMARK RESULTS")
        print("=" * 60)
        overall = aggregated.get("overall", {})
        print(f"  Overall Accuracy: {overall.get('accuracy', 0):.1f}%")
        print(f"  Overall F1:       {overall.get('f1', 0):.1f}%")
        print(f"  Overall BLEU-1:   {overall.get('bleu1', 0):.1f}%")

        print("\nPer-Category:")
        for cat, data in aggregated.get("categories", {}).items():
            print(f"  {data['name']:15s} — Acc: {data['accuracy']:.1f}%  "
                  f"F1: {data['f1']:.1f}%  ({data['count']} questions)")

        print("\nComparison:")
        for system, score in sorted(
            aggregated.get("comparison", {}).items(),
            key=lambda x: x[1], reverse=True,
        ):
            marker = " <-- US" if system == "memwire" else ""
            print(f"  {system:20s} {score:.1f}%{marker}")

        latency = aggregated.get("latency", {})
        print(f"\nLatency (recall): p50={latency.get('recall_p50', 0):.0f}ms "
              f"p95={latency.get('recall_p95', 0):.0f}ms "
              f"mean={latency.get('recall_mean', 0):.0f}ms")
        print(f"Results saved to {self.config.results_path}")

        self._emit_progress(stage="done", aggregated=aggregated)
        return aggregated
