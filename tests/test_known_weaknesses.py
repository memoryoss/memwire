"""Test 13: Known weaknesses — tests designed to expose limitations.

These tests probe the fundamental limits of a vector-only approach
(no LLM calls). Contradiction detection relies on displacement-based
tension detection and hybrid search (SPLADE).
"""

from tests.conftest import TEST_USER


class TestNegationAwareness:
    """Contradictions detected via displacement graph + hybrid search."""

    def test_contradictory_memories_recalled(self, memory):
        """Both sides of a contradiction should be retrievable."""
        memory.add(user_id=TEST_USER, messages=[
            {"role": "user", "content": "I am happy with the current vendor"},
            {"role": "user", "content": "I am not happy with the current vendor"},
        ])
        result = memory.recall("Is the user satisfied with the vendor?", user_id=TEST_USER)
        all_contents = set()
        for path in result.all_paths:
            for mem in path.memories:
                all_contents.add(mem.content)
        print(f"  Recalled: {all_contents}")
        assert any("happy" in c for c in all_contents)


class TestNumericReasoning:
    """Pure vector systems can't do math."""

    def test_budget_comparison(self, memory):
        """System can't tell 50k > 30k."""
        memory.add(user_id=TEST_USER, messages=[
            {"role": "user", "content": "Budget for Q1 is 50000 dollars"},
            {"role": "user", "content": "Budget for Q2 is 30000 dollars"},
        ])
        result = memory.recall("Which quarter has more budget?", user_id=TEST_USER)
        all_contents = set()
        for path in result.all_paths:
            for mem in path.memories:
                all_contents.add(mem.content)
        print(f"  Numeric comparison: {all_contents}")

    def test_date_ordering(self, memory):
        """System can't order dates."""
        memory.add(user_id=TEST_USER, messages=[
            {"role": "user", "content": "Meeting A is on March 5th"},
            {"role": "user", "content": "Meeting B is on March 20th"},
            {"role": "user", "content": "Meeting C is on March 12th"},
        ])
        result = memory.recall("What is the next upcoming meeting?", user_id=TEST_USER)
        all_contents = set()
        for path in result.all_paths:
            for mem in path.memories:
                all_contents.add(mem.content)
        print(f"  Date ordering: {all_contents}")


class TestNodeOverConsolidation:
    """The 0.85 merge threshold may incorrectly merge different concepts."""

    def test_homonym_separation(self, memory):
        """'Apple' company vs 'apple' fruit should be separate nodes."""
        memory.add(user_id=TEST_USER, messages=[
            {"role": "user", "content": "Apple released the new iPhone model"},
            {"role": "user", "content": "I bought a fresh apple from the market"},
        ])
        graph = memory._get_graph(TEST_USER)
        apple_nodes = [
            n for n in graph.nodes.values()
            if "apple" in n.token.lower()
        ]
        print(f"  Apple nodes: {[(n.node_id, n.token, len(n.memory_ids)) for n in apple_nodes]}")

    def test_bank_disambiguation(self, memory):
        """'bank' (financial) vs 'bank' (river) should ideally separate."""
        memory.add(user_id=TEST_USER, messages=[
            {"role": "user", "content": "I deposited my savings at the bank downtown"},
            {"role": "user", "content": "We had a picnic on the bank of the river"},
        ])
        graph = memory._get_graph(TEST_USER)
        bank_nodes = [
            n for n in graph.nodes.values()
            if "bank" in n.token.lower()
        ]
        print(f"  Bank nodes: {len(bank_nodes)} "
              f"(1=over-consolidated, 2=correctly separated)")


class TestDisplacementThreshold:
    """Low threshold (0.15) may create noise edges."""

    def test_unrelated_words_not_connected(self, memory):
        """Completely unrelated words should not be edge-connected."""
        memory.add(user_id=TEST_USER, messages=[
            {"role": "user", "content": "The elephant danced gracefully under moonlight"},
        ])
        stats = memory.get_stats(user_id=TEST_USER)
        ratio = stats["edges"] / max(stats["nodes"], 1)
        print(f"  Single sentence: {stats['nodes']} nodes, {stats['edges']} edges, "
              f"ratio: {ratio:.1f}")


class TestFeedbackDeadZone:
    """Alignment between 0.2 and 0.5 gets no feedback."""

    def test_moderate_alignment_ignored(self, memory):
        """Somewhat-related responses get zero feedback."""
        memory.add(user_id=TEST_USER, messages=[
            {"role": "user", "content": "Our team uses agile development methodology"},
        ])
        memory.recall("How does the team work?", user_id=TEST_USER)

        graph = memory._get_graph(TEST_USER)
        edges_before = {
            k: e.weight for k, e in graph.edges.items()
        }
        stats = memory.feedback(
            response="Good software development practices include code review",
            user_id=TEST_USER,
        )
        edges_after = {
            k: e.weight for k, e in graph.edges.items()
        }

        changed = sum(1 for k in edges_before
                       if k in edges_after and abs(edges_before[k] - edges_after[k]) > 0.001)
        print(f"  Moderate alignment: {changed} edges changed, stats={stats}")
        print(f"  Dead zone effect: {'NO edges changed' if changed == 0 else f'{changed} edges changed'}")


class TestTemporalAwareness:
    """Recency weighting now favors newer memories."""

    def test_old_vs_new_preference(self, memory):
        """Newer preference should rank higher via recency weighting."""
        memory.add(user_id=TEST_USER, messages=[
            {"role": "user", "content": "My favorite color is blue"},
        ])
        for i in range(10):
            memory.add(user_id=TEST_USER, messages=[{"role": "user", "content": f"Unrelated filler message {i}"}])
        memory.add(user_id=TEST_USER, messages=[
            {"role": "user", "content": "My favorite color is now green"},
        ])

        result = memory.recall("What is my favorite color?", user_id=TEST_USER)
        all_contents = []
        for path in result.all_paths:
            for mem in path.memories:
                if "color" in mem.content.lower():
                    all_contents.append(mem.content)
        print(f"  Temporal: {all_contents}")
        assert any("green" in c for c in all_contents), \
            f"Expected 'green' in recalled color memories: {all_contents}"
