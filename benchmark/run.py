"""CLI entry point for LOCOMO benchmark.

Usage:
    python -m benchmark.run                                        # full benchmark
    python -m benchmark.run --max-conversations 1 --max-questions 20  # quick test
    python -m benchmark.run --web --port 8001                      # web dashboard
"""

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(
        description="LOCOMO benchmark for memwire"
    )
    parser.add_argument(
        "--max-conversations", type=int, default=None,
        help="Limit number of conversations (default: all 10)",
    )
    parser.add_argument(
        "--max-questions", type=int, default=None,
        help="Limit questions per conversation (default: all)",
    )
    parser.add_argument(
        "--categories", type=int, nargs="+", default=[1, 2, 3, 4],
        help="Question categories to evaluate (default: 1 2 3 4)",
    )
    parser.add_argument(
        "--answer-model", type=str, default="gpt-4o-mini",
        help="Model for answer generation (default: gpt-4o-mini)",
    )
    parser.add_argument(
        "--judge-model", type=str, default="gpt-4o-mini",
        help="Model for LLM judge (default: gpt-4o-mini)",
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="Output file path (default: benchmark/results/results.json)",
    )
    parser.add_argument(
        "--web", action="store_true",
        help="Launch web dashboard instead of CLI",
    )
    parser.add_argument(
        "--port", type=int, default=8001,
        help="Web dashboard port (default: 8001)",
    )
    parser.add_argument(
        "--reset", action="store_true",
        help="Reset progress and start fresh",
    )

    args = parser.parse_args()

    from .config import BenchmarkConfig

    config = BenchmarkConfig(
        max_conversations=args.max_conversations,
        max_questions=args.max_questions,
        categories=args.categories,
        answer_model=args.answer_model,
        judge_model=args.judge_model,
        web_port=args.port,
    )

    if args.output:
        from pathlib import Path
        config.results_dir = Path(args.output).parent
        config.results_dir.mkdir(parents=True, exist_ok=True)

    if args.reset:
        if config.progress_path.exists():
            config.progress_path.unlink()
            print("Progress reset.")

    if args.web:
        from .locomo_web_benchmark import run_web_dashboard
        run_web_dashboard(config)
    else:
        from .locomo_runner import BenchmarkRunner
        runner = BenchmarkRunner(config=config)
        runner.run()


if __name__ == "__main__":
    main()
