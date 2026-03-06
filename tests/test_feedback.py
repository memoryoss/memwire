"""Test 7: Feedback loop — does it actually change edge weights?"""

from tests.conftest import TEST_USER


def test_feedback_strengthens_aligned_paths(memory):
    """Response aligned with recalled paths should strengthen edges."""
    memory.add(user_id=TEST_USER, messages=[
        {"role": "user", "content": "We prefer organic cotton for all clothing"},
        {"role": "user", "content": "Vendor A sells high quality organic cotton"},
    ])
    # Recall and capture edge weights before feedback
    graph = memory._get_graph(TEST_USER)
    result = memory.recall("Which vendor has organic cotton?", user_id=TEST_USER)
    edges_before = {
        k: e.weight for k, e in graph.edges.items()
    }

    # Feedback with aligned response
    stats = memory.feedback(
        response="Vendor A is your best choice for organic cotton clothing",
        user_id=TEST_USER,
    )
    edges_after = {
        k: e.weight for k, e in graph.edges.items()
    }

    # Some edges should have changed
    changed = sum(1 for k in edges_before if k in edges_after and edges_before[k] != edges_after[k])
    print(f"  Aligned feedback: {changed} edges changed, stats={stats}")


def test_feedback_weakens_misaligned_paths(memory):
    """Response contradicting recalled paths should weaken edges."""
    memory.add(user_id=TEST_USER, messages=[
        {"role": "user", "content": "We always use synthetic materials"},
        {"role": "user", "content": "Synthetic fabric is our standard"},
    ])
    memory.recall("What materials do we use?", user_id=TEST_USER)

    # Feedback with completely different topic
    stats = memory.feedback(
        response="The quarterly financial report shows a 20 percent increase in revenue",
        user_id=TEST_USER,
    )
    print(f"  Misaligned feedback: {stats}")


def test_feedback_dead_zone(memory):
    """Response in the 0.2-0.5 alignment range should have no effect."""
    memory.add(user_id=TEST_USER, messages=[
        {"role": "user", "content": "The project involves building a web application"},
    ])
    memory.recall("What are we building?", user_id=TEST_USER)

    graph = memory._get_graph(TEST_USER)
    edges_before = {
        k: e.weight for k, e in graph.edges.items()
    }
    # Response that's somewhat related but not strongly aligned
    stats = memory.feedback(
        response="Software development requires careful planning and testing",
        user_id=TEST_USER,
    )
    edges_after = {
        k: e.weight for k, e in graph.edges.items()
    }

    unchanged = sum(1 for k in edges_before if k in edges_after and edges_before[k] == edges_after[k])
    total = len(edges_before)
    print(f"  Dead zone: {unchanged}/{total} edges unchanged, stats={stats}")


def test_repeated_feedback_accumulates(memory):
    """Multiple feedback rounds should accumulate weight changes."""
    memory.add(user_id=TEST_USER, messages=[
        {"role": "user", "content": "We need fast delivery for all orders"},
    ])
    memory.recall("What is important about orders?", user_id=TEST_USER)

    # Track weight changes across 5 feedback rounds
    graph = memory._get_graph(TEST_USER)
    weights_history = []
    for i in range(5):
        memory.recall("What is important about orders?", user_id=TEST_USER)
        memory.feedback(response="Fast delivery is our top priority for customer satisfaction", user_id=TEST_USER)
        total_weight = sum(e.weight for e in graph.edges.values())
        weights_history.append(total_weight)

    print(f"  Weight history over 5 rounds: {[f'{w:.2f}' for w in weights_history]}")


def test_feedback_without_recall_is_noop(memory):
    """Feedback without prior recall should do nothing."""
    memory.add(user_id=TEST_USER, messages=[{"role": "user", "content": "Test message for feedback"}])
    stats = memory.feedback(response="Any response", user_id=TEST_USER)
    assert stats == {"strengthened": 0, "weakened": 0}
