"""Memory formatting for prompt injection into LLM context."""

from ..utils.types import RecallResult, RecallPath, KnowledgeChunk


class MemoryFormatter:
    """Formats recall results into text suitable for LLM prompt injection."""

    def format(self, result: RecallResult) -> str:
        """Format a RecallResult into a prompt-ready string."""
        if not result.all_paths and not result.knowledge:
            return ""

        sections = []

        if result.supporting:
            sections.append(self._format_section(
                "Relevant memories", result.supporting
            ))

        if result.knowledge:
            sections.append(self._format_knowledge(result.knowledge))

        if result.conflicting:
            sections.append(self._format_section(
                "Potentially conflicting memories (review carefully)",
                result.conflicting,
            ))

        return "\n\n".join(sections)

    def _format_section(self, header: str, paths: list[RecallPath]) -> str:
        """Format a group of paths into a labeled section."""
        lines = [f"[{header}]"]
        seen_contents = set()

        for i, path in enumerate(paths, 1):
            for memory in path.memories:
                if memory.content in seen_contents:
                    continue
                seen_contents.add(memory.content)
                category_tag = f" [{memory.category}]" if memory.category else ""
                lines.append(f"- {memory.content}{category_tag}")

        return "\n".join(lines)

    def _format_knowledge(self, chunks: list[KnowledgeChunk]) -> str:
        """Format knowledge chunks into a labeled section."""
        lines = ["[Relevant knowledge]"]
        for chunk in chunks:
            source = chunk.metadata.get("source", "")
            tag = f" [{source}]" if source else ""
            lines.append(f"- {chunk.content}{tag}")
        return "\n".join(lines)

    def format_compact(self, result: RecallResult) -> str:
        """Compact single-line format for token-limited contexts."""
        if not result.all_paths and not result.knowledge:
            return ""

        contents = []
        seen = set()
        for path in result.all_paths:
            for memory in path.memories:
                if memory.content not in seen:
                    seen.add(memory.content)
                    contents.append(memory.content)

        for chunk in result.knowledge:
            if chunk.content not in seen:
                seen.add(chunk.content)
                contents.append(chunk.content)

        return " | ".join(contents)

    def format_with_scores(self, result: RecallResult) -> str:
        """Format with relevance scores for debugging."""
        if not result.all_paths and not result.knowledge:
            return "No memories recalled."

        lines = [f"Query: {result.query}", ""]
        for i, path in enumerate(result.all_paths, 1):
            is_conflict = path in result.conflicting
            marker = "!" if is_conflict else " "
            lines.append(f"{marker} Path {i} (score: {path.score:.3f}):")
            for memory in path.memories:
                lines.append(f"    - [{memory.category}] {memory.content}")

        if result.knowledge:
            lines.append("\n  Knowledge:")
            for chunk in result.knowledge:
                source = chunk.metadata.get("source", "")
                tag = f" [{source}]" if source else ""
                lines.append(f"    - (score: {chunk.score:.3f}) {chunk.content}{tag}")

        if result.has_conflicts:
            lines.append(f"\nConflicts detected: {len(result.conflicting)} conflicting path(s)")

        return "\n".join(lines)
