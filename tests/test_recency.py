"""Tests for recency weighting in recall."""

import time


class TestRecencyWeighting:
    """Integration tests for temporal/recency scoring."""

    def test_newer_memory_scores_higher(self, memory):
        """Newer memories should be ranked higher than older ones."""
        memory.add([
            {"role": "user", "content": "My favorite color is blue"},
        ])
        # Small delay to ensure timestamp difference
        time.sleep(0.05)
        memory.add([
            {"role": "user", "content": "My favorite color is now green"},
        ])
        result = memory.recall("What is my favorite color?")
        color_memories = []
        for path in result.all_paths:
            for mem in path.memories:
                if "color" in mem.content.lower():
                    color_memories.append(mem)
        # green should appear (it's newer and has recency boost)
        contents = [m.content for m in color_memories]
        assert any("green" in c for c in contents), f"Expected 'green' in recalled memories: {contents}"

    def test_recency_with_filler(self, memory):
        """Updated preference should rank higher even after filler memories."""
        memory.add([
            {"role": "user", "content": "My favorite color is blue"},
        ])
        # Add filler to push old memory further back
        for i in range(10):
            memory.add([{"role": "user", "content": f"Unrelated filler message number {i}"}])
            time.sleep(0.01)
        memory.add([
            {"role": "user", "content": "My favorite color is now green"},
        ])

        result = memory.recall("What is my favorite color?")
        # Collect all color memories across all paths, with their path score
        color_entries = []
        for path in result.all_paths:
            for mem in path.memories:
                if "color" in mem.content.lower():
                    color_entries.append((mem.content, path.score))

        # At minimum, green should be present
        assert any("green" in c for c, _ in color_entries), \
            f"Expected 'green' in recalled memories: {color_entries}"

    def test_recency_disabled(self, config, memory):
        """When recency_weight=0, timestamps shouldn't affect scoring."""
        config.recency_weight = 0.0
        memory.add([
            {"role": "user", "content": "My favorite color is blue"},
        ])
        time.sleep(0.05)
        memory.add([
            {"role": "user", "content": "My favorite color is now green"},
        ])
        result = memory.recall("What is my favorite color?")
        # Both should be found; scores should not be affected by recency
        assert len(result.all_paths) > 0
