"""Basic memwire-sdk usage: add, recall, search, feedback."""

from memwire_sdk import MemWireClient

client = MemWireClient("http://localhost:8000", api_key="your-api-key")

USER_ID = "alice"

# store some memories
records = client.add(USER_ID, [
    {"role": "user", "content": "I prefer dark mode and concise answers"},
    {"role": "user", "content": "My favorite language is Python"},
    {"role": "assistant", "content": "Got it! I'll keep responses concise."},
])
print(f"Stored {len(records)} memories")

# recall relevant context for a query
result = client.recall("How should I format responses?", USER_ID)
print(f"\nRecall ({len(result.supporting)} paths):")
print(result.formatted)

if result.has_tensions:
    print(f"Conflicts detected: {len(result.conflicting)} paths")

# search by similarity
results = client.search("programming preferences", USER_ID, top_k=5)
print(f"\nSearch results:")
for r in results:
    print(f"  [{r.score:.2f}] {r.memory.content}")

# feedback to reinforce good recall paths
client.feedback("I'll use dark mode and keep it concise in Python", USER_ID)
print("\nFeedback applied")

# check stats
stats = client.stats(USER_ID)
print(f"\nStats: {stats}")

client.close()
