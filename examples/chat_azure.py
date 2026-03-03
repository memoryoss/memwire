"""Azure OpenAI variant of chat.py.

Required environment variables
-------------------------------
AZURE_OPENAI_API_KEY      — Your Azure OpenAI resource key
AZURE_OPENAI_ENDPOINT     — e.g. https://<resource>.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT   — The deployment name (acts as model id)
AZURE_OPENAI_API_VERSION  — API version, e.g. 2024-02-01 (optional, defaulted below)

Optional
--------
QDRANT_URL  — Set to http://localhost:6333 to use a running Qdrant server.
              Omit to use embedded file-based mode (chat_qdrant/).
"""

import os
import sys
import io
import signal

# Suppress all HF/transformer noise before any imports
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["HF_HUB_VERBOSITY"] = "error"

import logging

logging.disable(logging.WARNING)

from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Azure OpenAI client
# ---------------------------------------------------------------------------
_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
_api_key = os.getenv("AZURE_OPENAI_API_KEY")
_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")

if not _endpoint or not _api_key:
    raise EnvironmentError(
        "Azure OpenAI requires AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY "
        "to be set in the environment (or .env file)."
    )

client = AzureOpenAI(
    api_key=_api_key,
    azure_endpoint=_endpoint,
    api_version=_api_version,
)

# For Azure, the *deployment name* is passed as the model argument.
MODEL = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")

# ---------------------------------------------------------------------------
# MemWire setup
# ---------------------------------------------------------------------------
print("Loading memory model...", end=" ", flush=True)
_real_stderr = sys.stderr
sys.stderr = io.StringIO()
try:
    from memwire import MemWire, MemWireConfig

    # --- Qdrant connection modes ---
    # 1. Local server (run: docker run -p 6333:6333 qdrant/qdrant)
    #    qdrant_url="http://localhost:6333"
    # 2. Embedded (no server, files in ./chat_qdrant/)
    #    qdrant_path="chat_qdrant"

    qdrant_url = os.getenv("QDRANT_URL")  # set to http://localhost:6333 for server mode

    config = MemWireConfig(
        org_id="demo_org",
        database_url="sqlite:///chat_memory.db",
        qdrant_url=qdrant_url,
        qdrant_path=None if qdrant_url else "chat_qdrant",
        qdrant_collection_prefix="chat_",
    )
    memory = MemWire(config=config)
    USER_ID = "chat_user"
finally:
    sys.stderr = _real_stderr
    logging.disable(logging.NOTSET)

stats = memory.get_stats(user_id=USER_ID)
print(f"done! ({stats['memories']} memories, {stats['nodes']} nodes loaded)")

conversation_history: list[dict[str, str]] = []

SYSTEM_PROMPT = (
    "You are a helpful assistant with access to a memory system. "
    "When memory context is provided, use it to give personalized, "
    "consistent responses. Reference past conversations naturally."
)


def build_messages(user_input: str) -> list[dict[str, str]]:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Recall relevant memories
    print("  [recalling memories...]", end="", flush=True)
    result = memory.recall(user_input, user_id=USER_ID)
    if result.formatted:
        messages.append(
            {
                "role": "system",
                "content": f"Relevant memory context:\n{result.formatted}",
            }
        )
        print(f" found {len(result.supporting)} paths", flush=True)
    else:
        print(" no relevant memories", flush=True)

    # Recent conversation (last 20 msgs)
    messages.extend(conversation_history[-20:])
    messages.append({"role": "user", "content": user_input})
    return messages


def chat(user_input: str) -> str:
    messages = build_messages(user_input)

    # Stream the response so tokens appear in real-time
    print("\nAssistant: ", end="", flush=True)
    stream = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        stream=True,
    )
    chunks = []
    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta.content
        if delta:
            print(delta, end="", flush=True)
            chunks.append(delta)
    print()  # newline after streaming completes

    assistant_msg = "".join(chunks)

    # Track in conversation history
    conversation_history.append({"role": "user", "content": user_input})
    conversation_history.append({"role": "assistant", "content": assistant_msg})

    # Store to vector memory (runs embedding per token — takes a moment)
    memory.add(user_id=USER_ID, messages=[
        {"role": "user", "content": user_input},
        {"role": "assistant", "content": assistant_msg},
    ])

    # Feedback to strengthen relevant memory paths
    memory.feedback(response=assistant_msg, user_id=USER_ID)

    return assistant_msg


def shutdown():
    print("\nSaving memory...", end=" ", flush=True)
    memory.close()
    print("done. Goodbye!")
    sys.exit(0)


def main():
    # Handle Ctrl+C gracefully
    signal.signal(signal.SIGINT, lambda *_: shutdown())

    print(f"\nChat with Memory  [Azure OpenAI · deployment: {MODEL}]")
    print(
        "  Commands: quit | memory | search | kb load <file.txt> | kb search <query> | kb list"
    )
    print("-" * 60)

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except EOFError:
            shutdown()

        if not user_input:
            continue
        if user_input.lower() == "quit":
            shutdown()
        if user_input.lower() == "memory":
            s = memory.get_stats(user_id=USER_ID)
            print(
                f"\n[Memory] {s['memories']} memories | {s['nodes']} nodes | {s['edges']} edges | {s['knowledge_bases']} KBs"
            )
            continue
        if user_input.lower() == "search":
            try:
                query = input("Search query: ").strip()
            except EOFError:
                continue
            if query:
                results = memory.search(query, user_id=USER_ID, top_k=5)
                if results:
                    print("\n[Search Results]")
                    for record, score in results:
                        print(f"  [{score:.2f}] ({record.category}) {record.content}")
                else:
                    print("  No memories found.")
            continue

        # Knowledge base commands
        if user_input.lower().startswith("kb load "):
            filepath = user_input[8:].strip()
            if not os.path.isfile(filepath):
                print(f"  File not found: {filepath}")
                continue
            if not filepath.endswith(".txt"):
                print("  Only .txt files are supported.")
                continue
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                text = f.read().strip()
            if not text:
                print("  File is empty.")
                continue
            # Chunk on double-newlines, fallback to single-newlines
            paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
            if len(paragraphs) <= 1:
                paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
            chunks = [
                {"content": p, "metadata": {"source": os.path.basename(filepath)}}
                for p in paragraphs
                if len(p) >= 10
            ]
            if not chunks:
                print("  No usable chunks found.")
                continue
            kb_name = os.path.basename(filepath).rsplit(".", 1)[0]
            print(
                f"  Loading {len(chunks)} chunks from {filepath}...",
                end=" ",
                flush=True,
            )
            kb_id = memory.add_knowledge(kb_name, chunks, user_id=USER_ID)
            print(f"done! KB: {kb_id}")
            continue

        if user_input.lower().startswith("kb search "):
            query = user_input[10:].strip()
            if query:
                results = memory.search_knowledge(query, user_id=USER_ID, top_k=5)
                if results:
                    print("\n[Knowledge Results]")
                    for chunk in results:
                        source = chunk.metadata.get("source", "")
                        tag = f" [{source}]" if source else ""
                        print(f"  [{chunk.score:.2f}] {chunk.content}{tag}")
                else:
                    print("  No knowledge found.")
            continue

        if user_input.lower() == "kb list":
            s = memory.get_stats(user_id=USER_ID)
            print(f"\n[Knowledge Bases] {s['knowledge_bases']} loaded")
            continue

        chat(user_input)


if __name__ == "__main__":
    main()
