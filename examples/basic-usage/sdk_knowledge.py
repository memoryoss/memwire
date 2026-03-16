"""memwire-sdk knowledge base: add documents, search, delete."""

from memwire_sdk import MemWireClient

USER_ID = "alice"

with MemWireClient("http://localhost:8000", api_key="your-api-key") as client:
    # add a knowledge base with chunks
    kb_id = client.add_knowledge(
        "company-faq",
        [
            {"content": "Our return policy allows returns within 30 days of purchase."},
            {"content": "Free shipping is available on orders over $50."},
            {"content": "Business hours are Monday to Friday, 9 AM to 5 PM EST."},
            {"content": "Premium members get 20% off all orders.", "metadata": {"source": "pricing"}},
        ],
        USER_ID,
    )
    print(f"Created knowledge base: {kb_id}")

    # search knowledge
    chunks = client.search_knowledge("shipping costs", USER_ID, limit=3)
    print(f"\nKnowledge search results:")
    for chunk in chunks:
        print(f"  [{chunk.score:.2f}] {chunk.content}")

    # delete when done
    client.delete_knowledge(kb_id, USER_ID)
    print(f"\nDeleted knowledge base: {kb_id}")
