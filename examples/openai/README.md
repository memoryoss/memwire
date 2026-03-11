# MemWire × OpenAI Examples

FastAPI web UI with streaming responses and memory visualisation, powered by OpenAI.

## Requirements

- Python 3.10+
- An [OpenAI API key](https://platform.openai.com/api-keys)

---

## Run locally

```bash
cp .env.example .env        # fill in OPENAI_API_KEY
pip install -r requirements.txt
uvicorn web_chat:app --reload
```

Then open http://localhost:8000.

---

## Run with Docker (web UI + Qdrant)

```bash
cp .env.example .env        # fill in OPENAI_API_KEY
docker compose up
```

Then open http://localhost:8000.

To stop:

```bash
docker compose down
```
