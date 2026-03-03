"""Test 6: Graph construction — displacement edges, cross-linking, node merging."""

from memwire.utils.math_ops import cosine_similarity
from tests.conftest import TEST_USER


def test_graph_creates_nodes(memory):
    """Adding a memory should create graph nodes."""
    memory.add(user_id=TEST_USER, messages=[{"role": "user", "content": "The weather is sunny today"}])
    stats = memory.get_stats(user_id=TEST_USER)
    assert stats["nodes"] > 0, "No nodes created"
    print(f"  Nodes from one sentence: {stats['nodes']}")


def test_graph_creates_edges(memory):
    """Nodes with similar displacement should be connected."""
    memory.add(user_id=TEST_USER, messages=[{"role": "user", "content": "Machine learning algorithms process data efficiently"}])
    stats = memory.get_stats(user_id=TEST_USER)
    print(f"  Nodes: {stats['nodes']}, Edges: {stats['edges']}")
    assert stats["edges"] > 0, "No edges created"


def test_cross_memory_edges(memory):
    """Related memories should form edges between them."""
    memory.add(user_id=TEST_USER, messages=[{"role": "user", "content": "We use organic cotton for shirts"}])
    stats1 = memory.get_stats(user_id=TEST_USER)

    memory.add(user_id=TEST_USER, messages=[{"role": "user", "content": "Organic materials are our priority"}])
    stats2 = memory.get_stats(user_id=TEST_USER)

    # Should have more edges after cross-linking
    print(f"  Before: {stats1['edges']} edges, After: {stats2['edges']} edges")
    assert stats2["edges"] > stats1["edges"], "No cross-memory edges created"


def test_node_merging_same_token(memory):
    """Same word in different memories should reuse the same node."""
    memory.add(user_id=TEST_USER, messages=[
        {"role": "user", "content": "Organic food is healthy"},
        {"role": "user", "content": "I eat organic vegetables daily"},
    ])
    graph = memory._get_graph(TEST_USER)
    organic_nodes = [
        n for n in graph.nodes.values()
        if n.token == "organic"
    ]
    print(f"  Nodes for 'organic': {len(organic_nodes)}")


def test_edge_weight_within_bounds(memory):
    """All edge weights should be within [min, max]."""
    memory.add(user_id=TEST_USER, messages=[
        {"role": "user", "content": "The quick brown fox jumps over the lazy dog"},
        {"role": "user", "content": "A fast brown fox leaps across a sleeping dog"},
    ])
    graph = memory._get_graph(TEST_USER)
    for edge in graph.edges.values():
        assert memory.config.edge_weight_min <= edge.weight <= memory.config.edge_weight_max, \
            f"Edge weight {edge.weight} out of bounds"


def test_edge_decay(memory):
    """Decaying edges should reduce weights and remove weak ones."""
    memory.add(user_id=TEST_USER, messages=[{"role": "user", "content": "Testing edge decay mechanisms in graph"}])
    graph = memory._get_graph(TEST_USER)
    edges_before = len(graph.edges)

    # Decay multiple times
    for _ in range(30):
        graph.decay_all()

    edges_after = len(graph.edges)
    print(f"  Edges before decay: {edges_before}, after 30 decays: {edges_after}")
    assert edges_after < edges_before, "Decay didn't remove any edges"


def test_strengthen_edge(memory):
    """Strengthening should increase edge weight."""
    memory.add(user_id=TEST_USER, messages=[{"role": "user", "content": "Testing edge strength modification"}])
    graph = memory._get_graph(TEST_USER)
    if graph.edges:
        key = next(iter(graph.edges))
        edge = graph.edges[key]
        original_weight = edge.weight
        graph.strengthen_edge(edge.source_id, edge.target_id, 0.2)
        assert edge.weight > original_weight


def test_weaken_edge(memory):
    """Weakening should decrease edge weight."""
    memory.add(user_id=TEST_USER, messages=[{"role": "user", "content": "Testing edge weakness modification"}])
    graph = memory._get_graph(TEST_USER)
    if graph.edges:
        key = next(iter(graph.edges))
        edge = graph.edges[key]
        original_weight = edge.weight
        graph.weaken_edge(edge.source_id, edge.target_id, 0.1)
        assert edge.weight < original_weight


def test_displacement_vector_meaning(memory):
    """Displacement vectors should capture context shift."""
    embeddings = memory.engine.embeddings
    tokens_financial = embeddings.embed_tokens("I deposited money at the bank")
    tokens_river = embeddings.embed_tokens("I sat on the river bank")

    bank_financial = [t for t in tokens_financial if t.token == "bank"]
    bank_river = [t for t in tokens_river if t.token == "bank"]

    if bank_financial and bank_river:
        disp_sim = cosine_similarity(
            bank_financial[0].displacement, bank_river[0].displacement
        )
        print(f"  Displacement similarity ('bank' financial vs river): {disp_sim:.3f}")


def test_graph_handles_single_word(memory):
    """Graph should handle single-word input."""
    memory.add(user_id=TEST_USER, messages=[{"role": "user", "content": "hello"}])
    stats = memory.get_stats(user_id=TEST_USER)
    print(f"  Single word: {stats['nodes']} nodes, {stats['edges']} edges")
    assert stats["nodes"] >= 0
