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
