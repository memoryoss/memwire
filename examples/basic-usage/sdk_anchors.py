"""memwire-sdk custom classification anchors."""

from memwire_sdk import MemWireClient

with MemWireClient("http://localhost:8000", api_key="your-api-key") as client:
    USER_ID = "alice"

    # add custom classification categories
    client.add_category("complaint", "I'm unhappy with the service", USER_ID)
    client.add_category("praise", "Great job, I love this product", USER_ID)
    client.add_category("question", "How does this work?", USER_ID)

    # add some memories
    client.add(USER_ID, [
        {"role": "user", "content": "Your product broke after one week"},
        {"role": "user", "content": "This is the best tool I've ever used"},
        {"role": "user", "content": "Can you explain the pricing tiers?"},
    ])

    # search by category
    complaints = client.search("issues", USER_ID, category="complaint", limit=5)
    print("Complaints:")
    for r in complaints:
        print(f"  [{r.score:.2f}] {r.memory.content}")

    praise = client.search("feedback", USER_ID, category="praise", limit=5)
    print("\nPraise:")
    for r in praise:
        print(f"  [{r.score:.2f}] {r.memory.content}")
