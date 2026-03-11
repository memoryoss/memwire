from memwire import MemWire, MemWireConfig

config = MemWireConfig(
    qdrant_path="./memwire_data",  # local vector store
    qdrant_collection_prefix="app_",
)
memory = MemWire(config=config)

USER_ID = "alice"

# Add messages to memory
records = memory.add(
    user_id=USER_ID,
    messages=[{"role": "user", "content": "I prefer dark mode and short answers."}],
)
for r in records:
    print(f"[stored] ({r.category}) {r.content}")

# Recall relevant context for a query
result = memory.recall("How should I format my answers?", user_id=USER_ID)
if result.formatted:
    print(result.formatted)
    # → "alice prefers dark mode and short answers."

# Inject recalled context into your LLM prompt
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
]
if result.formatted:
    messages.append(
        {"role": "system", "content": f"Memory context:\n{result.formatted}"}
    )
messages.append({"role": "user", "content": "How should I format my answers?"})

# After you get the LLM response, reinforce the memory paths that were used
memory.feedback(response="<assistant response here>", user_id=USER_ID)

# Search memories by keyword / semantic similarity
hits = memory.search("dark mode", user_id=USER_ID, top_k=5)
for record, score in hits:
    print(f"[{score:.2f}] ({record.category}) {record.content}")

# Inspect stats
stats = memory.get_stats(user_id=USER_ID)
print(stats)  # {"memories": 1, "nodes": ..., "edges": ..., "knowledge_bases": 0}

# Always close to flush background writes
memory.close()
