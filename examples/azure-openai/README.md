# MemWire × Azure OpenAI Example

FastAPI web UI with streaming responses and memory visualisation, powered by Azure OpenAI.

## Requirements

- Python 3.10+
- An Azure OpenAI resource with a deployed model

## Required environment variables

| Variable | Description |
|---|---|
| `AZURE_OPENAI_API_KEY` | Your Azure OpenAI resource key |
| `AZURE_OPENAI_ENDPOINT` | e.g. `https://<resource>.openai.azure.com/` |
| `AZURE_OPENAI_DEPLOYMENT` | The deployment name (acts as model id) |
| `AZURE_OPENAI_API_VERSION` | API version, e.g. `2024-02-01` (defaults to `2024-02-01`) |

---

## Run locally

```bash
cp .env.example .env        # fill in Azure credentials
pip install -r requirements.txt
uvicorn web_chat:app --reload
```

Then open http://localhost:8000.

---

## Run with Docker (web UI + Qdrant)

```bash
cp .env.example .env        # fill in Azure credentials
docker compose up
```

Then open http://localhost:8000.

To stop:

```bash
docker compose down
```

---

## Try it out — sample conversation

The following exchange shows how MemWire builds and uses memory across a realistic coding-assistant session. Paste these messages one at a time in the chat UI and watch the memory panel grow.

### Turn 1 — share your context

> **You:** Hi! I'm working on a Python FastAPI service that processes IoT sensor data from smart home devices. I'm using PostgreSQL with async SQLAlchemy, deploying on Azure Container Apps, and I prefer type hints and async/await throughout.

The assistant introduces itself and notes your setup. MemWire stores your tech stack, deployment target, and coding style as structured memories.

---

### Turn 2 — ask a task-specific question

> **You:** I need to add rate limiting to the API so a single device can't flood the endpoint.

Because MemWire recalled that you're on FastAPI, the assistant will suggest a FastAPI-native approach (e.g. `slowapi` or middleware with Redis) and frame the answer around Azure Container Apps deployment — without you repeating any of that context.

---

### Turn 3 — reference a preference set earlier

> **You:** Can you show me the rate-limit middleware as a reusable async dependency? Keep it fully typed.

The assistant already knows your async preference and type-hint style from Turn 1. The code it returns uses `async def`, proper type annotations, and fits your existing stack — no re-prompting required.

---

### Turn 4 — return in a new session

Close the browser tab, restart the server, and open a fresh chat. Then ask:

> **You:** What was I building again?

MemWire persists memory to SQLite across restarts. The assistant will summarise your IoT sensor project, tech stack, and the rate-limiting work — even in a brand-new conversation window.

---

### What to observe

| Memory panel metric | What it tells you |
|---|---|
| **Recall ms** | How fast relevant memories were retrieved before the LLM call |
| **Paths** | Number of supporting memory entries injected as context |
| **Memories / Nodes** | Cumulative store size — grows with each turn |
| **Feedback score** | Automated quality signal written back after each response |

The `/api/search` endpoint (or the Search tab in the UI) lets you query the memory store directly — try searching `"rate limiting"` after Turn 3 to confirm the conversation was indexed.
