"""memwire-sdk document ingestion: parse, chunk, and store files automatically.

Requires: pip install "memwire[ingest]"
Supports PDF, DOCX, HTML, TXT, Markdown, and more via unstructured.
"""

from memwire import MemWire, MemWireConfig

USER_ID = "alice"

# initialize with embedded qdrant (no server needed)
config = MemWireConfig(
    qdrant_path="./ingest_demo_data",
    qdrant_collection_prefix="ingest_",
)
memory = MemWire(config=config)

# --- ingest a single file ---
# auto-detects format, chunks by section boundaries, embeds, and stores
kb_id = memory.ingest(
    "sample_report.txt",
    name="quarterly-report",
    user_id=USER_ID,
)
print(f"Ingested file -> kb_id: {kb_id}")

# --- search the ingested knowledge ---
chunks = memory.search_knowledge("revenue growth", user_id=USER_ID, top_k=3)
print(f"\nSearch results ({len(chunks)} chunks):")
for chunk in chunks:
    print(f"  [{chunk.score:.2f}] {chunk.content[:100]}...")
    if chunk.metadata:
        print(f"         source: {chunk.metadata.get('source', 'n/a')}")

# --- ingest with custom chunking ---
kb_id_2 = memory.ingest(
    "detailed_specs.pdf",
    name="product-specs",
    user_id=USER_ID,
    chunk_max_characters=800,   # smaller chunks for precision
    chunk_overlap=100,
)
print(f"\nIngested PDF -> kb_id: {kb_id_2}")

# --- use recall to get both memories and knowledge ---
# add some conversational memory first
memory.add(
    user_id=USER_ID,
    messages=[
        {"role": "user", "content": "We need to hit 20% revenue growth this quarter"},
        {"role": "assistant", "content": "I'll track that target alongside the report data."},
    ],
)

result = memory.recall("What do we know about revenue targets?", user_id=USER_ID)
print(f"\nRecall result:")
print(f"  {len(result.supporting)} memory paths")
print(f"  {len(result.knowledge)} knowledge chunks")
print(result.formatted)

# cleanup
memory.delete_knowledge(kb_id)
memory.delete_knowledge(kb_id_2)
memory.close()

print("\nDone.")
