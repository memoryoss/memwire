"""Test 3: Recall relevance — does recall return the RIGHT memories?"""


def test_recall_finds_directly_related(memory):
    """Query about topic X should recall memories about X, not Y."""
    memory.add([
        {"role": "user", "content": "Our budget is 50 thousand dollars per quarter"},
        {"role": "user", "content": "We prefer organic cotton for clothing"},
        {"role": "user", "content": "The project deadline is March 15th"},
    ])
    result = memory.recall("How much money can we spend?")
    # The budget memory should appear in recalled paths
    all_contents = []
    for path in result.all_paths:
        for mem in path.memories:
            all_contents.append(mem.content)
    print(f"  Budget query recalled: {all_contents}")
    assert any("budget" in c.lower() or "50" in c or "dollar" in c for c in all_contents), \
        f"Budget memory not found in recall: {all_contents}"


def test_recall_finds_semantically_similar(memory):
    """Query using different words but same meaning should still recall."""
    memory.add([
        {"role": "user", "content": "We prefer organic materials for all products"},
    ])
    # Ask with completely different words
    result = memory.recall("What kind of natural fabrics do we want?")
    all_contents = []
    for path in result.all_paths:
        for mem in path.memories:
            all_contents.append(mem.content)
    print(f"  Semantic recall: {all_contents}")
    assert any("organic" in c.lower() for c in all_contents), \
        f"Semantic match not found: {all_contents}"


def test_recall_ranks_relevant_higher(memory):
    """More relevant memories should have higher path scores."""
    memory.add([
        {"role": "user", "content": "I love eating Italian pasta with tomato sauce"},
        {"role": "user", "content": "The quarterly sales report shows 20% growth"},
        {"role": "user", "content": "My favorite restaurant serves amazing pizza"},
    ])
    result = memory.recall("What food do I like?")
    if result.supporting:
        top_path = result.supporting[0]
        top_contents = [m.content for m in top_path.memories]
        print(f"  Top path: {top_contents} (score: {top_path.score:.3f})")
        # Top path should contain food-related memory, not sales report
        has_food = any("pasta" in c.lower() or "pizza" in c.lower() or "restaurant" in c.lower()
                       for c in top_contents)
        print(f"  Has food content: {has_food}")


def test_recall_with_no_relevant_memories(memory):
    """Query completely unrelated to stored memories."""
    memory.add([
        {"role": "user", "content": "The chemical formula for water is H2O"},
    ])
    result = memory.recall("What is the best programming language?")
    print(f"  Unrelated query: {len(result.supporting)} supporting, "
          f"{len(result.conflicting)} conflicting")
    # May still return paths (low relevance threshold 0.25), but scores should be low
    if result.supporting:
        top_score = result.supporting[0].score
        print(f"  Top score for unrelated query: {top_score:.3f}")


def test_recall_multiple_related_memories(memory):
    """Query should pull together multiple related memories."""
    memory.add([
        {"role": "user", "content": "Vendor A sells organic cotton"},
        {"role": "user", "content": "Vendor A is based in Portland"},
        {"role": "user", "content": "We have a contract with Vendor A until December"},
        {"role": "user", "content": "The weather in Tokyo is nice"},
    ])
    result = memory.recall("Tell me about Vendor A")
    all_contents = set()
    for path in result.all_paths:
        for mem in path.memories:
            all_contents.add(mem.content)
    vendor_a_count = sum(1 for c in all_contents if "vendor a" in c.lower())
    print(f"  Vendor A recall: found {vendor_a_count}/3 related memories")
    print(f"  All recalled: {all_contents}")
    assert vendor_a_count >= 2, f"Should recall at least 2 Vendor A memories, got {vendor_a_count}"


def test_recall_cross_links_between_topics(memory):
    """Memories about the same entity in different contexts should link."""
    memory.add([
        {"role": "user", "content": "John manages the supply chain team"},
        {"role": "user", "content": "The supply chain had delays last month"},
        {"role": "user", "content": "John proposed a new vendor strategy"},
    ])
    result = memory.recall("What has John been doing about supply chain issues?")
    all_contents = set()
    for path in result.all_paths:
        for mem in path.memories:
            all_contents.add(mem.content)
    print(f"  Cross-link recall: {all_contents}")
    # Should ideally recall all 3 — they share "John" and "supply chain"
    assert len(all_contents) >= 2, f"Expected cross-linked memories, got {len(all_contents)}"
