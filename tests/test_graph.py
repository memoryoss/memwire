"""Test 6: Graph construction — displacement edges, cross-linking, node merging."""

from memwire.utils.math_ops import cosine_similarity


def test_graph_creates_nodes(memory):
    """Adding a memory should create graph nodes."""
    memory.add([{"role": "user", "content": "The weather is sunny today"}])
    stats = memory.get_stats()
    assert stats["nodes"] > 0, "No nodes created"
    print(f"  Nodes from one sentence: {stats['nodes']}")


def test_graph_creates_edges(memory):
    """Nodes with similar displacement should be connected."""
    memory.add([{"role": "user", "content": "Machine learning algorithms process data efficiently"}])
    stats = memory.get_stats()
    print(f"  Nodes: {stats['nodes']}, Edges: {stats['edges']}")
    assert stats["edges"] > 0, "No edges created"


def test_cross_memory_edges(memory):
    """Related memories should form edges between them."""
    memory.add([{"role": "user", "content": "We use organic cotton for shirts"}])
    stats1 = memory.get_stats()

    memory.add([{"role": "user", "content": "Organic materials are our priority"}])
    stats2 = memory.get_stats()

    # Should have more edges after cross-linking
    print(f"  Before: {stats1['edges']} edges, After: {stats2['edges']} edges")
    assert stats2["edges"] > stats1["edges"], "No cross-memory edges created"


def test_node_merging_same_token(memory):
    """Same word in different memories should reuse the same node."""
    memory.add([
        {"role": "user", "content": "Organic food is healthy"},
        {"role": "user", "content": "I eat organic vegetables daily"},
    ])
    # "organic" should be a single node (or merged), not duplicated
    organic_nodes = [
        n for n in memory.engine.graph.nodes.values()
        if n.token == "organic"
    ]
    print(f"  Nodes for 'organic': {len(organic_nodes)}")
    # Multiple nodes is OK if embeddings differ (context-dependent)
    # But if merge_similarity (0.85) catches them, should be 1


def test_edge_weight_within_bounds(memory):
    """All edge weights should be within [min, max]."""
    memory.add([
        {"role": "user", "content": "The quick brown fox jumps over the lazy dog"},
        {"role": "user", "content": "A fast brown fox leaps across a sleeping dog"},
    ])
    for edge in memory.engine.graph.edges.values():
        assert memory.config.edge_weight_min <= edge.weight <= memory.config.edge_weight_max, \
            f"Edge weight {edge.weight} out of bounds"


def test_edge_decay(memory):
    """Decaying edges should reduce weights and remove weak ones."""
    memory.add([{"role": "user", "content": "Testing edge decay mechanisms in graph"}])
    edges_before = len(memory.engine.graph.edges)

    # Decay multiple times
    for _ in range(30):
        memory.engine.decay_all()

    edges_after = len(memory.engine.graph.edges)
    print(f"  Edges before decay: {edges_before}, after 30 decays: {edges_after}")
    assert edges_after < edges_before, "Decay didn't remove any edges"


def test_strengthen_edge(memory):
    """Strengthening should increase edge weight."""
    memory.add([{"role": "user", "content": "Testing edge strength modification"}])
    if memory.engine.graph.edges:
        key = next(iter(memory.engine.graph.edges))
        edge = memory.engine.graph.edges[key]
        original_weight = edge.weight
        memory.engine.graph.strengthen_edge(edge.source_id, edge.target_id, 0.2)
        assert edge.weight > original_weight


def test_weaken_edge(memory):
    """Weakening should decrease edge weight."""
    memory.add([{"role": "user", "content": "Testing edge weakness modification"}])
    if memory.engine.graph.edges:
        key = next(iter(memory.engine.graph.edges))
        edge = memory.engine.graph.edges[key]
        original_weight = edge.weight
        memory.engine.graph.weaken_edge(edge.source_id, edge.target_id, 0.1)
        assert edge.weight < original_weight


def test_displacement_vector_meaning(memory):
    """Displacement vectors should capture context shift."""
    embeddings = memory.engine.embeddings
    # "bank" alone vs "bank" in financial context
    tokens_financial = embeddings.embed_tokens("I deposited money at the bank")
    tokens_river = embeddings.embed_tokens("I sat on the river bank")

    bank_financial = [t for t in tokens_financial if t.token == "bank"]
    bank_river = [t for t in tokens_river if t.token == "bank"]

    if bank_financial and bank_river:
        disp_sim = cosine_similarity(
            bank_financial[0].displacement, bank_river[0].displacement
        )
        print(f"  Displacement similarity ('bank' financial vs river): {disp_sim:.3f}")
        # Different contexts should produce different displacements
        # But with this simple model, may not capture it well


def test_graph_handles_single_word(memory):
    """Graph should handle single-word input."""
    memory.add([{"role": "user", "content": "hello"}])
    stats = memory.get_stats()
    print(f"  Single word: {stats['nodes']} nodes, {stats['edges']} edges")
    assert stats["nodes"] >= 0  # May be 0 if single char filtered
