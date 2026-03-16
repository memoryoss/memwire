"""memwire-sdk multi-user isolation: each user has separate memory."""

from memwire_sdk import MemWireClient

with MemWireClient("http://localhost:8000", api_key="your-api-key") as client:
    # user A stores preferences
    client.add("alice", [
        {"role": "user", "content": "I'm vegetarian and love Italian food"},
    ])

    # user B stores different preferences
    client.add("bob", [
        {"role": "user", "content": "I'm a steak lover and prefer Mexican food"},
    ])

    # recall is isolated per user
    alice_recall = client.recall("food recommendations", "alice")
    bob_recall = client.recall("food recommendations", "bob")

    print("Alice's memory:")
    print(f"  {alice_recall.formatted or 'No memories yet'}\n")

    print("Bob's memory:")
    print(f"  {bob_recall.formatted or 'No memories yet'}\n")

    # stats are scoped per user
    print(f"Alice stats: {client.get_stats('alice')}")
    print(f"Bob stats: {client.get_stats('bob')}")
