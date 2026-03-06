"""Test 9: Semantic understanding — paraphrases, synonyms, indirect references."""

from tests.conftest import TEST_USER


def test_paraphrase_recall(memory):
    """Paraphrased query should find the original memory."""
    memory.add(user_id=TEST_USER, messages=[
        {"role": "user", "content": "Our company requires all reports submitted by Friday"},
    ])
    result = memory.recall("When is the deadline for turning in documents each week?", user_id=TEST_USER)
    all_contents = set()
    for path in result.all_paths:
        for mem in path.memories:
            all_contents.add(mem.content)
    has_match = any("friday" in c.lower() or "report" in c.lower() for c in all_contents)
    print(f"  Paraphrase recall: found={has_match}, contents={all_contents}")


def test_synonym_matching(memory):
    """Synonyms should be linked."""
    memory.add(user_id=TEST_USER, messages=[
        {"role": "user", "content": "The automobile needs an oil change"},
    ])
    result = memory.recall("When should I service my car?", user_id=TEST_USER)
    all_contents = set()
    for path in result.all_paths:
        for mem in path.memories:
            all_contents.add(mem.content)
    has_match = any("automobile" in c.lower() for c in all_contents)
    print(f"  Synonym recall (car->automobile): found={has_match}")


def test_implicit_reference(memory):
    """Implicit references to earlier context."""
    memory.add(user_id=TEST_USER, messages=[
        {"role": "user", "content": "John is our lead engineer"},
        {"role": "user", "content": "He designed the new authentication system"},
    ])
    result = memory.recall("What did John design?", user_id=TEST_USER)
    all_contents = set()
    for path in result.all_paths:
        for mem in path.memories:
            all_contents.add(mem.content)
    print(f"  Implicit reference: {all_contents}")


def test_negation_understanding(memory):
    """Negation should ideally be distinguished."""
    memory.add(user_id=TEST_USER, messages=[
        {"role": "user", "content": "We do NOT accept late submissions"},
        {"role": "user", "content": "We accept all submissions regardless of timing"},
    ])
    result = memory.recall("Can I submit late?", user_id=TEST_USER)
    all_contents = set()
    for path in result.all_paths:
        for mem in path.memories:
            all_contents.add(mem.content)
    print(f"  Negation test: {all_contents}")
    print(f"  Tensions detected: {result.has_tensions}")


def test_abstract_to_concrete_matching(memory):
    """Abstract concept should match concrete examples."""
    memory.add(user_id=TEST_USER, messages=[
        {"role": "user", "content": "We value sustainability in all business decisions"},
    ])
    result = memory.recall("Should we use recycled packaging materials?", user_id=TEST_USER)
    all_contents = set()
    for path in result.all_paths:
        for mem in path.memories:
            all_contents.add(mem.content)
    has_match = any("sustainability" in c.lower() for c in all_contents)
    print(f"  Abstract->concrete: found={has_match}")


def test_multi_hop_reasoning(memory):
    """Connecting facts that require chaining."""
    memory.add(user_id=TEST_USER, messages=[
        {"role": "user", "content": "Alice manages the marketing team"},
        {"role": "user", "content": "The marketing team launched the new campaign"},
        {"role": "user", "content": "The new campaign increased sales by 30 percent"},
    ])
    result = memory.recall("How did Alice impact sales?", user_id=TEST_USER)
    all_contents = set()
    for path in result.all_paths:
        for mem in path.memories:
            all_contents.add(mem.content)
    print(f"  Multi-hop: {all_contents}")


def test_contextual_disambiguation(memory):
    """Same word, different meanings, should have different graph paths."""
    memory.add(user_id=TEST_USER, messages=[
        {"role": "user", "content": "The Python programming language is very popular"},
        {"role": "user", "content": "A python snake can grow up to 30 feet long"},
    ])
    result_code = memory.recall("What programming language should I learn?", user_id=TEST_USER)
    result_animal = memory.recall("Tell me about large reptiles", user_id=TEST_USER)

    code_contents = set()
    for path in result_code.all_paths:
        for mem in path.memories:
            code_contents.add(mem.content)

    animal_contents = set()
    for path in result_animal.all_paths:
        for mem in path.memories:
            animal_contents.add(mem.content)

    print(f"  Code query: {code_contents}")
    print(f"  Animal query: {animal_contents}")
