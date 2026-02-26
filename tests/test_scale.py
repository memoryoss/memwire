"""Test 12: Scale behavior — performance with many memories."""

import time


def test_scale_50_memories(memory):
    """Add 50 memories and verify recall still works."""
    messages = [
        {"role": "user", "content": f"This is memory number {i} about topic {i % 5}"}
        for i in range(50)
    ]
    start = time.time()
    memory.add(messages)
    add_time = time.time() - start

    stats = memory.get_stats()
    print(f"  50 memories: {stats['nodes']} nodes, {stats['edges']} edges")
    print(f"  Add time: {add_time:.2f}s")

    start = time.time()
    result = memory.recall("topic 3")
    recall_time = time.time() - start
    print(f"  Recall time: {recall_time:.2f}s, paths: {len(result.all_paths)}")
    assert len(result.all_paths) > 0


def test_scale_recall_returns_relevant_at_scale(memory):
    """With many memories, recall should still find relevant ones."""
    # Add 30 unrelated memories
    noise = [
        {"role": "user", "content": f"Random noise sentence number {i} about nothing"}
        for i in range(30)
    ]
    memory.add(noise)

    # Add 3 specific target memories
    memory.add([
        {"role": "user", "content": "Our vendor Acme Corp delivers organic silk"},
        {"role": "user", "content": "Acme Corp is based in Portland Oregon"},
        {"role": "user", "content": "The contract with Acme Corp expires in June"},
    ])

    result = memory.recall("Tell me about Acme Corp")
    all_contents = set()
    for path in result.all_paths:
        for mem in path.memories:
            all_contents.add(mem.content)

    acme_count = sum(1 for c in all_contents if "acme" in c.lower())
    noise_count = sum(1 for c in all_contents if "noise" in c.lower())
    print(f"  Scale relevance: {acme_count} Acme memories, {noise_count} noise in results")
    assert acme_count >= 2, f"Should find at least 2 Acme memories, found {acme_count}"


def test_graph_density_at_scale(memory):
    """Graph shouldn't explode with too many edges at scale."""
    for i in range(20):
        memory.add([
            {"role": "user", "content": f"The team discussed project milestone {i} in the meeting"}
        ])

    stats = memory.get_stats()
    ratio = stats["edges"] / max(stats["nodes"], 1)
    print(f"  20 memories: {stats['nodes']} nodes, {stats['edges']} edges, "
          f"ratio: {ratio:.1f} edges/node")
    # Flag if graph is extremely dense (>50 edges per node)
    if ratio > 50:
        print(f"  WARNING: Very dense graph ({ratio:.1f} edges/node)")


def test_search_performance_at_scale(memory):
    """Search should remain responsive with many memories."""
    messages = [
        {"role": "user", "content": f"Record {i}: status update for project alpha"}
        for i in range(40)
    ]
    memory.add(messages)

    start = time.time()
    results = memory.search("project alpha", top_k=5)
    search_time = time.time() - start
    print(f"  Search over 40 memories: {search_time:.3f}s, {len(results)} results")
    assert search_time < 5.0, f"Search too slow: {search_time}s"
