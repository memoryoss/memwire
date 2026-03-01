"""FastAPI web chat UI with streaming responses, performance metrics, and memory visualization.

Azure OpenAI variant of web_chat.py.

Required environment variables
-------------------------------
AZURE_OPENAI_API_KEY      — Your Azure OpenAI resource key
AZURE_OPENAI_ENDPOINT     — e.g. https://<resource>.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT   — The deployment name (acts as model id)
AZURE_OPENAI_API_VERSION  — API version, e.g. 2024-02-01 (optional, defaulted below)

Optional
--------
QDRANT_URL  — Set to http://localhost:6333 to use a running Qdrant server.
              Omit to use embedded file-based mode (web_chat_qdrant/).
"""

import os
import sys
import io
import json
import time
import asyncio
import logging
from contextlib import asynccontextmanager

# Suppress HF/transformer noise before any imports
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["HF_HUB_VERBOSITY"] = "error"

from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from dotenv import load_dotenv
from openai import AzureOpenAI

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

openai_client = AzureOpenAI(
    api_key=_api_key,
    azure_endpoint=_endpoint,
    api_version=_api_version,
)

# For Azure, the *deployment name* is passed as the model argument.
MODEL = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")

# --- Globals (set during lifespan) ---
memory = None
conversation_history: list[dict[str, str]] = []

SYSTEM_PROMPT = (
    "You are a helpful assistant with access to a memory system. "
    "When memory context is provided, use it to give personalized, "
    "consistent responses. Reference past conversations naturally."
)


async def run_sync(fn, *args):
    """Run a blocking function in a thread executor."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, fn, *args)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global memory
    print("Loading memory model...", end=" ", flush=True)
    _real_stderr = sys.stderr
    sys.stderr = io.StringIO()
    logging.disable(logging.WARNING)
    try:
        from memwire import MemWire, MemWireConfig

        qdrant_url = os.getenv("QDRANT_URL")  # http://localhost:6333 for server mode

        config = MemWireConfig(
            user_id="web_chat_user",
            database_url="sqlite:///web_chat_memory.db",
            qdrant_url=qdrant_url,
            qdrant_path=None if qdrant_url else "web_chat_qdrant",
            qdrant_collection_prefix="web_",
        )
        memory = MemWire(user_id="web_chat_user", config=config)
    finally:
        sys.stderr = _real_stderr
        logging.disable(logging.NOTSET)

    stats = memory.get_stats()
    print(f"done! ({stats['memories']} memories, {stats['nodes']} nodes loaded)")
    print(
        f"Starting web chat on http://localhost:8000  [Azure OpenAI · deployment: {MODEL}]"
    )

    yield

    print("\nSaving memory...", end=" ", flush=True)
    memory.close()
    print("done. Goodbye!")


app = FastAPI(lifespan=lifespan)


# --- API Endpoints ---


@app.get("/api/health")
async def api_health():
    try:
        stats = await run_sync(memory.get_stats)
        return JSONResponse({"status": "ready", "stats": stats})
    except Exception as e:
        return JSONResponse({"status": "booting", "error": str(e)}, status_code=503)


@app.get("/api/stats")
async def api_stats():
    stats = await run_sync(memory.get_stats)
    return JSONResponse(stats)


@app.post("/api/chat")
async def api_chat(request: Request):
    body = await request.json()
    user_input = body.get("message", "").strip()
    if not user_input:
        return JSONResponse({"error": "Empty message"}, status_code=400)

    async def event_stream():
        t_start = time.perf_counter()

        # 1. Recall with timing
        t0 = time.perf_counter()
        result = await run_sync(memory.recall, user_input)
        t_recall = time.perf_counter() - t0

        paths_count = len(result.supporting) if result.supporting else 0
        context_len = len(result.formatted) if result.formatted else 0
        yield f"data: {json.dumps({'type': 'recall', 'paths': paths_count, 'context_chars': context_len, 'recall_ms': round(t_recall * 1000, 1)})}\n\n"

        # 2. Build messages
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if result.formatted:
            messages.append(
                {
                    "role": "system",
                    "content": f"Relevant memory context:\n{result.formatted}",
                }
            )
        messages.extend(conversation_history[-20:])
        messages.append({"role": "user", "content": user_input})

        # 3. Stream Azure OpenAI with timing
        queue = asyncio.Queue()

        def stream_openai():
            s = openai_client.chat.completions.create(
                model=MODEL,
                messages=messages,
                stream=True,
            )
            for chunk in s:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta.content
                if delta:
                    queue.put_nowait(delta)
            queue.put_nowait(None)

        t_gen_start = time.perf_counter()
        loop = asyncio.get_event_loop()
        task = loop.run_in_executor(None, stream_openai)

        chunks = []
        token_count = 0
        first_token_time = None

        while True:
            token = await queue.get()
            if token is None:
                break
            if first_token_time is None:
                first_token_time = time.perf_counter()
            chunks.append(token)
            token_count += 1
            yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

        await task
        t_gen_end = time.perf_counter()
        t_gen_total = t_gen_end - t_gen_start
        t_ttft = (first_token_time - t_gen_start) if first_token_time else 0
        tps = token_count / t_gen_total if t_gen_total > 0 else 0

        assistant_msg = "".join(chunks)

        # 4. Update conversation history
        conversation_history.append({"role": "user", "content": user_input})
        conversation_history.append({"role": "assistant", "content": assistant_msg})

        # 5. Add to memory with timing
        t0 = time.perf_counter()
        await run_sync(
            memory.add,
            [
                {"role": "user", "content": user_input},
                {"role": "assistant", "content": assistant_msg},
            ],
        )
        t_mem_add = time.perf_counter() - t0

        # 6. Feedback with timing
        t0 = time.perf_counter()
        feedback = await run_sync(memory.feedback, assistant_msg)
        t_feedback = time.perf_counter() - t0

        # 7. Final stats + all timing
        stats = await run_sync(memory.get_stats)
        t_total = time.perf_counter() - t_start

        yield f"data: {json.dumps({'type': 'done', 'stats': stats, 'feedback': feedback, 'perf': {'recall_ms': round(t_recall * 1000, 1), 'ttft_ms': round(t_ttft * 1000, 1), 'gen_ms': round(t_gen_total * 1000, 1), 'tokens': token_count, 'tokens_per_sec': round(tps, 1), 'mem_add_ms': round(t_mem_add * 1000, 1), 'feedback_ms': round(t_feedback * 1000, 1), 'total_ms': round(t_total * 1000, 1), 'output_chars': len(assistant_msg)}})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/api/search")
async def api_search(request: Request):
    body = await request.json()
    query = body.get("query", "").strip()
    top_k = body.get("top_k", 5)
    if not query:
        return JSONResponse({"error": "Empty query"}, status_code=400)

    t0 = time.perf_counter()
    results = await run_sync(memory.search, query, None, top_k)
    elapsed = time.perf_counter() - t0
    return JSONResponse(
        {
            "results": [
                {
                    "content": record.content,
                    "category": record.category,
                    "score": round(score, 3),
                    "role": record.role,
                }
                for record, score in results
            ],
            "search_ms": round(elapsed * 1000, 1),
        }
    )


@app.post("/api/knowledge/add")
async def api_knowledge_add(request: Request):
    body = await request.json()
    name = body.get("name", "").strip()
    chunks = body.get("chunks", [])
    if not name or not chunks:
        return JSONResponse({"error": "name and chunks required"}, status_code=400)

    t0 = time.perf_counter()
    kb_id = await run_sync(memory.add_knowledge, name, chunks)
    elapsed = time.perf_counter() - t0
    return JSONResponse(
        {"kb_id": kb_id, "chunks": len(chunks), "add_ms": round(elapsed * 1000, 1)}
    )


@app.post("/api/knowledge/search")
async def api_knowledge_search(request: Request):
    body = await request.json()
    query = body.get("query", "").strip()
    top_k = body.get("top_k", 5)
    if not query:
        return JSONResponse({"error": "Empty query"}, status_code=400)

    t0 = time.perf_counter()
    results = await run_sync(memory.search_knowledge, query, top_k)
    elapsed = time.perf_counter() - t0
    return JSONResponse(
        {
            "results": [
                {
                    "content": chunk.content,
                    "kb_id": chunk.kb_id,
                    "score": round(chunk.score, 3),
                    "metadata": chunk.metadata,
                }
                for chunk in results
            ],
            "search_ms": round(elapsed * 1000, 1),
        }
    )


@app.post("/api/knowledge/delete")
async def api_knowledge_delete(request: Request):
    body = await request.json()
    kb_id = body.get("kb_id", "").strip()
    if not kb_id:
        return JSONResponse({"error": "kb_id required"}, status_code=400)
    await run_sync(memory.delete_knowledge, kb_id)
    return JSONResponse({"status": "deleted", "kb_id": kb_id})


@app.post("/api/knowledge/upload")
async def api_knowledge_upload(file: UploadFile = File(...), name: str = Form("")):
    """Upload a .txt file as a knowledge base. Splits on double-newlines into chunks."""
    if not file.filename.endswith(".txt"):
        return JSONResponse({"error": "Only .txt files are supported"}, status_code=400)

    raw = await file.read()
    text = raw.decode("utf-8", errors="replace").strip()
    if not text:
        return JSONResponse({"error": "File is empty"}, status_code=400)

    # Use filename (without extension) as KB name if not provided
    kb_name = name.strip() or file.filename.rsplit(".", 1)[0]

    # Split into chunks: double-newline paragraphs, fallback to single-newline blocks
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if len(paragraphs) <= 1:
        # Single block — split on single newlines
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

    # Filter out very short chunks (< 10 chars) and build chunk dicts
    chunks = [
        {"content": p, "metadata": {"source": file.filename}}
        for p in paragraphs
        if len(p) >= 10
    ]

    if not chunks:
        return JSONResponse(
            {"error": "No usable content chunks found"}, status_code=400
        )

    t0 = time.perf_counter()
    kb_id = await run_sync(memory.add_knowledge, kb_name, chunks)
    elapsed = time.perf_counter() - t0

    return JSONResponse(
        {
            "kb_id": kb_id,
            "name": kb_name,
            "chunks": len(chunks),
            "add_ms": round(elapsed * 1000, 1),
            "source": file.filename,
        }
    )


@app.post("/api/clear")
async def api_clear():
    conversation_history.clear()
    return JSONResponse({"status": "cleared"})


# --- Frontend ---


HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Vector Memory Chat</title>
<style>
  :root {
    --bg-primary: #0f1117;
    --bg-secondary: #161822;
    --bg-tertiary: #1c1f2e;
    --bg-card: #1e2133;
    --border: #2a2d3e;
    --border-accent: #3a3d5c;
    --text-primary: #e1e4ed;
    --text-secondary: #8b8fa3;
    --text-muted: #5a5e72;
    --accent-red: #ef4565;
    --accent-cyan: #64ffda;
    --accent-blue: #64b5f6;
    --accent-green: #81c784;
    --accent-amber: #ffb74d;
    --accent-purple: #b388ff;
  }

  * { margin: 0; padding: 0; box-sizing: border-box; }

  body {
    font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', 'Consolas', monospace;
    background: var(--bg-primary);
    color: var(--text-primary);
    height: 100vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  /* === HEADER === */
  header {
    background: var(--bg-secondary);
    padding: 10px 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
    z-index: 10;
  }

  .header-left {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .header-left h1 {
    font-size: 15px;
    color: var(--accent-red);
    font-weight: 700;
    letter-spacing: -0.3px;
  }

  .model-tag {
    font-size: 11px;
    padding: 2px 8px;
    border-radius: 4px;
    background: var(--bg-tertiary);
    color: var(--text-muted);
    border: 1px solid var(--border);
  }

  #stats-bar {
    font-size: 12px;
    color: var(--text-secondary);
    display: flex;
    gap: 14px;
  }

  .stat-chip {
    display: flex;
    align-items: center;
    gap: 5px;
    padding: 3px 10px;
    border-radius: 4px;
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
  }

  .stat-chip .label { color: var(--text-muted); font-size: 11px; }
  .stat-chip .val { color: var(--accent-cyan); font-weight: 600; font-variant-numeric: tabular-nums; }

  .btn-upload {
    padding: 4px 12px;
    border-radius: 4px;
    border: 1px solid var(--border);
    background: var(--bg-tertiary);
    color: var(--accent-green);
    font-size: 11px;
    font-weight: 600;
    cursor: pointer;
    font-family: inherit;
    transition: all 0.15s;
    display: flex;
    align-items: center;
    gap: 5px;
  }
  .btn-upload:hover { background: var(--bg-card); border-color: var(--accent-green); }
  .btn-upload:disabled { opacity: 0.5; cursor: not-allowed; }

  .upload-progress {
    font-size: 11px;
    color: var(--accent-amber);
    display: none;
    align-items: center;
    gap: 5px;
  }
  .upload-progress.active { display: flex; }

  /* === MAIN LAYOUT === */
  .main-container {
    flex: 1;
    display: flex;
    overflow: hidden;
  }

  /* === CHAT === */
  #chat-area {
    flex: 1;
    overflow-y: auto;
    padding: 16px 20px;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .msg-group {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .msg-group-user { align-items: flex-end; }
  .msg-group-assistant { align-items: flex-start; }

  .msg-label {
    font-size: 10px;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    padding: 0 4px;
    margin-bottom: 2px;
  }

  .msg {
    max-width: 72%;
    padding: 10px 14px;
    border-radius: 10px;
    line-height: 1.6;
    font-size: 13px;
    white-space: pre-wrap;
    word-wrap: break-word;
  }

  .msg-user {
    background: #1a2744;
    color: #c5d0e6;
    border: 1px solid #263354;
    border-bottom-right-radius: 3px;
  }

  .msg-assistant {
    background: var(--bg-card);
    color: var(--text-primary);
    border: 1px solid var(--border);
    border-bottom-left-radius: 3px;
  }

  .msg-system {
    align-self: center;
    color: var(--text-muted);
    font-size: 11px;
    padding: 4px 14px;
    max-width: 90%;
    text-align: center;
    border: 1px dashed var(--border);
    border-radius: 6px;
  }

  /* === PERF STRIP (under each assistant msg) === */
  .perf-strip {
    display: flex;
    gap: 4px;
    flex-wrap: wrap;
    margin-top: 4px;
    max-width: 72%;
  }

  .perf-tag {
    font-size: 10px;
    padding: 1px 7px;
    border-radius: 3px;
    font-weight: 500;
    letter-spacing: 0.2px;
    font-variant-numeric: tabular-nums;
  }

  .perf-tag-recall   { background: #112240; color: var(--accent-blue); border: 1px solid #1a3a5c; }
  .perf-tag-speed    { background: #0d2818; color: var(--accent-green); border: 1px solid #1a3c2e; }
  .perf-tag-memory   { background: #2a1a0a; color: var(--accent-amber); border: 1px solid #3c2e1a; }
  .perf-tag-feedback { background: #1a0a2a; color: var(--accent-purple); border: 1px solid #2e1a3c; }
  .perf-tag-time     { background: #1a1a1a; color: var(--text-secondary); border: 1px solid var(--border); }

  /* === PERF PANEL (right sidebar) === */
  #perf-panel {
    width: 280px;
    background: var(--bg-secondary);
    border-left: 1px solid var(--border);
    overflow-y: auto;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    transition: width 0.2s;
  }

  #perf-panel.collapsed { width: 0; overflow: hidden; border: none; }

  .panel-header {
    padding: 10px 14px;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: var(--text-muted);
    border-bottom: 1px solid var(--border);
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-shrink: 0;
  }

  .panel-toggle {
    background: none;
    border: none;
    color: var(--text-muted);
    cursor: pointer;
    font-size: 14px;
    padding: 2px 6px;
    border-radius: 3px;
  }
  .panel-toggle:hover { background: var(--bg-tertiary); color: var(--text-primary); }

  .panel-section {
    padding: 12px 14px;
    border-bottom: 1px solid var(--border);
  }

  .panel-section-title {
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    color: var(--text-muted);
    margin-bottom: 8px;
  }

  /* Timing waterfall */
  .waterfall { display: flex; flex-direction: column; gap: 6px; }

  .wf-row {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .wf-label {
    font-size: 11px;
    color: var(--text-secondary);
    width: 70px;
    flex-shrink: 0;
    text-align: right;
  }

  .wf-bar-bg {
    flex: 1;
    height: 14px;
    background: var(--bg-primary);
    border-radius: 3px;
    overflow: hidden;
    position: relative;
  }

  .wf-bar {
    height: 100%;
    border-radius: 3px;
    min-width: 2px;
    transition: width 0.3s ease;
  }

  .wf-value {
    font-size: 10px;
    color: var(--text-muted);
    width: 55px;
    text-align: right;
    font-variant-numeric: tabular-nums;
    flex-shrink: 0;
  }

  .bar-recall   { background: var(--accent-blue); }
  .bar-ttft     { background: var(--accent-amber); }
  .bar-gen      { background: var(--accent-green); }
  .bar-mem      { background: var(--accent-purple); }
  .bar-feedback { background: var(--accent-cyan); }

  /* Big metrics */
  .big-metrics {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
  }

  .big-metric {
    padding: 8px;
    background: var(--bg-primary);
    border-radius: 6px;
    border: 1px solid var(--border);
    text-align: center;
  }

  .big-metric .num {
    font-size: 18px;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
  }

  .big-metric .unit {
    font-size: 10px;
    color: var(--text-muted);
    display: block;
    margin-top: 2px;
  }

  .num-green  { color: var(--accent-green); }
  .num-blue   { color: var(--accent-blue); }
  .num-amber  { color: var(--accent-amber); }
  .num-cyan   { color: var(--accent-cyan); }
  .num-purple { color: var(--accent-purple); }
  .num-red    { color: var(--accent-red); }

  /* Memory detail list */
  .mem-detail-row {
    display: flex;
    justify-content: space-between;
    padding: 3px 0;
    font-size: 11px;
  }
  .mem-detail-row .k { color: var(--text-muted); }
  .mem-detail-row .v { color: var(--text-primary); font-variant-numeric: tabular-nums; }

  /* Search results */
  .search-result {
    background: var(--bg-card);
    border-left: 3px solid var(--accent-cyan);
    padding: 8px 12px;
    margin: 4px 0;
    border-radius: 0 6px 6px 0;
    font-size: 12px;
    max-width: 80%;
  }

  .search-header {
    display: flex;
    gap: 8px;
    margin-bottom: 4px;
    align-items: center;
  }

  .search-score { color: var(--accent-cyan); font-weight: 700; font-size: 11px; }
  .search-category { color: var(--accent-red); font-size: 10px; padding: 1px 6px; border: 1px solid var(--border); border-radius: 3px; }
  .search-time { color: var(--text-muted); font-size: 10px; margin-left: auto; }

  /* === INPUT BAR === */
  #input-bar {
    display: flex;
    padding: 10px 20px;
    background: var(--bg-secondary);
    border-top: 1px solid var(--border);
    gap: 10px;
    flex-shrink: 0;
  }

  #message-input {
    flex: 1;
    padding: 10px 14px;
    border-radius: 6px;
    border: 1px solid var(--border);
    background: var(--bg-primary);
    color: var(--text-primary);
    font-size: 13px;
    font-family: inherit;
    outline: none;
    transition: border-color 0.15s;
  }

  #message-input:focus { border-color: var(--accent-red); }
  #message-input::placeholder { color: var(--text-muted); }

  .input-actions { display: flex; gap: 6px; }

  .btn {
    padding: 8px 16px;
    border-radius: 6px;
    border: 1px solid var(--border);
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    font-family: inherit;
    transition: all 0.15s;
  }

  .btn-primary {
    background: var(--accent-red);
    color: white;
    border-color: var(--accent-red);
  }
  .btn-primary:hover { background: #d63a57; }
  .btn-primary:disabled { background: var(--bg-tertiary); color: var(--text-muted); border-color: var(--border); cursor: not-allowed; }

  .btn-ghost {
    background: transparent;
    color: var(--text-secondary);
  }
  .btn-ghost:hover { background: var(--bg-tertiary); color: var(--text-primary); }

  /* Scrollbar */
  ::-webkit-scrollbar { width: 5px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
  ::-webkit-scrollbar-thumb:hover { background: var(--border-accent); }

  /* Cursor animation */
  .typing-cursor {
    display: inline-block;
    width: 2px;
    height: 13px;
    background: var(--accent-red);
    margin-left: 1px;
    vertical-align: text-bottom;
    animation: blink 0.6s infinite;
  }

  @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }

  /* Phase indicator while streaming */
  .phase-indicator {
    font-size: 11px;
    color: var(--text-muted);
    padding: 4px 0;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .phase-dot {
    width: 6px; height: 6px;
    border-radius: 50%;
    animation: pulse 1s infinite;
  }

  @keyframes pulse { 0%, 100% { opacity: 0.4; } 50% { opacity: 1; } }

  /* Empty state */
  .empty-state {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 10px;
    color: var(--text-muted);
  }

  .empty-state .title { font-size: 16px; color: var(--text-secondary); }
  .empty-state .hint { font-size: 12px; }
  .empty-state .commands { font-size: 11px; margin-top: 8px; color: var(--text-muted); }
  .empty-state .commands code { background: var(--bg-tertiary); padding: 2px 6px; border-radius: 3px; }
</style>
</head>
<body>

<header>
  <div class="header-left">
    <h1>MemWire</h1>
    <span class="model-tag" id="model-tag">Azure OpenAI</span>
  </div>
  <div id="stats-bar">
    <div class="stat-chip"><span class="label">mem</span><span class="val" id="stat-memories">-</span></div>
    <div class="stat-chip"><span class="label">nodes</span><span class="val" id="stat-nodes">-</span></div>
    <div class="stat-chip"><span class="label">edges</span><span class="val" id="stat-edges">-</span></div>
    <div class="stat-chip"><span class="label">KBs</span><span class="val" id="stat-kbs">-</span></div>
    <input type="file" id="kb-file-input" accept=".txt" style="display:none" multiple>
    <button class="btn-upload" id="kb-upload-btn" onclick="document.getElementById('kb-file-input').click()">+ Upload KB</button>
    <span class="upload-progress" id="upload-progress">uploading...</span>
  </div>
</header>

<div class="main-container">
  <div id="chat-area">
    <div class="empty-state" id="empty-state">
      <div class="title">Vector Memory Chat</div>
      <div class="hint">Send a message to start chatting with memory-augmented AI</div>
      <div class="commands">
        Commands: <code>/search query</code> <code>/kb add name|text</code> <code>/kb search query</code> <code>/clear</code> <code>/stats</code> <code>/perf</code>
      </div>
    </div>
  </div>

  <div id="perf-panel">
    <div class="panel-header">
      <span>Performance</span>
      <button class="panel-toggle" onclick="togglePanel()" title="Toggle panel">&times;</button>
    </div>
    <div id="panel-content">
      <div class="panel-section">
        <div class="panel-section-title">Last Response</div>
        <div class="big-metrics" id="big-metrics">
          <div class="big-metric"><span class="num num-green" id="pm-tps">-</span><span class="unit">tok/sec</span></div>
          <div class="big-metric"><span class="num num-amber" id="pm-ttft">-</span><span class="unit">TTFT ms</span></div>
          <div class="big-metric"><span class="num num-blue" id="pm-tokens">-</span><span class="unit">tokens</span></div>
          <div class="big-metric"><span class="num num-red" id="pm-total">-</span><span class="unit">total ms</span></div>
        </div>
      </div>
      <div class="panel-section">
        <div class="panel-section-title">Timing Waterfall</div>
        <div class="waterfall" id="waterfall">
          <div class="wf-row"><span class="wf-label">recall</span><div class="wf-bar-bg"><div class="wf-bar bar-recall" id="wb-recall" style="width:0%"></div></div><span class="wf-value" id="wv-recall">-</span></div>
          <div class="wf-row"><span class="wf-label">TTFT</span><div class="wf-bar-bg"><div class="wf-bar bar-ttft" id="wb-ttft" style="width:0%"></div></div><span class="wf-value" id="wv-ttft">-</span></div>
          <div class="wf-row"><span class="wf-label">generate</span><div class="wf-bar-bg"><div class="wf-bar bar-gen" id="wb-gen" style="width:0%"></div></div><span class="wf-value" id="wv-gen">-</span></div>
          <div class="wf-row"><span class="wf-label">mem add</span><div class="wf-bar-bg"><div class="wf-bar bar-mem" id="wb-mem" style="width:0%"></div></div><span class="wf-value" id="wv-mem">-</span></div>
          <div class="wf-row"><span class="wf-label">feedback</span><div class="wf-bar-bg"><div class="wf-bar bar-feedback" id="wb-feedback" style="width:0%"></div></div><span class="wf-value" id="wv-feedback">-</span></div>
        </div>
      </div>
      <div class="panel-section">
        <div class="panel-section-title">Details</div>
        <div id="detail-list">
          <div class="mem-detail-row"><span class="k">recall paths</span><span class="v" id="pd-paths">-</span></div>
          <div class="mem-detail-row"><span class="k">context chars</span><span class="v" id="pd-ctx">-</span></div>
          <div class="mem-detail-row"><span class="k">output chars</span><span class="v" id="pd-out">-</span></div>
          <div class="mem-detail-row"><span class="k">strengthened</span><span class="v" id="pd-str">-</span></div>
          <div class="mem-detail-row"><span class="k">weakened</span><span class="v" id="pd-weak">-</span></div>
        </div>
      </div>
      <div class="panel-section">
        <div class="panel-section-title">Memory State</div>
        <div id="mem-state-list">
          <div class="mem-detail-row"><span class="k">total memories</span><span class="v" id="pd-mem">-</span></div>
          <div class="mem-detail-row"><span class="k">graph nodes</span><span class="v" id="pd-nodes">-</span></div>
          <div class="mem-detail-row"><span class="k">graph edges</span><span class="v" id="pd-edges">-</span></div>
          <div class="mem-detail-row"><span class="k">knowledge bases</span><span class="v" id="pd-kbs">-</span></div>
        </div>
      </div>
    </div>
  </div>
</div>

<div id="input-bar">
  <input type="text" id="message-input" placeholder="Type a message... (/search, /kb search, /clear, /stats)" autocomplete="off">
  <div class="input-actions">
    <button class="btn btn-ghost" onclick="togglePanel()" title="Toggle perf panel">Perf</button>
    <button class="btn btn-primary" id="send-btn">Send</button>
  </div>
</div>

<script>
const chatArea = document.getElementById('chat-area');
const input = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');
const perfPanel = document.getElementById('perf-panel');
const emptyState = document.getElementById('empty-state');

let sending = false;
let lastPerf = null;

function scrollBottom() {
  chatArea.scrollTop = chatArea.scrollHeight;
}

function removeEmpty() {
  if (emptyState) emptyState.remove();
}

function togglePanel() {
  perfPanel.classList.toggle('collapsed');
}

function escapeHtml(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

function addPhase(text, color) {
  const div = document.createElement('div');
  div.className = 'phase-indicator';
  div.innerHTML = '<span class="phase-dot" style="background:' + color + '"></span>' + escapeHtml(text);
  chatArea.appendChild(div);
  scrollBottom();
  return div;
}

function addSystemMessage(text) {
  removeEmpty();
  const div = document.createElement('div');
  div.className = 'msg msg-system';
  div.textContent = text;
  chatArea.appendChild(div);
  scrollBottom();
}

function addSearchResults(results, searchMs) {
  const timeTag = searchMs !== undefined ? ' in ' + searchMs + 'ms' : '';
  for (const r of results) {
    const div = document.createElement('div');
    div.className = 'search-result';
    div.innerHTML =
      '<div class="search-header">'
      + '<span class="search-score">' + r.score.toFixed(3) + '</span>'
      + '<span class="search-category">' + escapeHtml(r.category) + '</span>'
      + (timeTag ? '<span class="search-time">' + timeTag + '</span>' : '')
      + '</div>'
      + '<div>' + escapeHtml(r.content) + '</div>';
    chatArea.appendChild(div);
  }
  scrollBottom();
}

function fmtMs(ms) {
  if (ms >= 1000) return (ms / 1000).toFixed(2) + 's';
  return Math.round(ms) + 'ms';
}

function updateWaterfall(perf) {
  const maxMs = perf.total_ms || 1;
  const items = [
    ['recall', perf.recall_ms],
    ['ttft', perf.ttft_ms],
    ['gen', perf.gen_ms],
    ['mem', perf.mem_add_ms],
    ['feedback', perf.feedback_ms],
  ];
  for (const [key, val] of items) {
    const pct = Math.min((val / maxMs) * 100, 100);
    document.getElementById('wb-' + key).style.width = pct + '%';
    document.getElementById('wv-' + key).textContent = fmtMs(val);
  }
}

function updatePerfPanel(perf, feedback, stats, recallPaths, contextChars) {
  document.getElementById('pm-tps').textContent = perf.tokens_per_sec;
  document.getElementById('pm-ttft').textContent = Math.round(perf.ttft_ms);
  document.getElementById('pm-tokens').textContent = perf.tokens;
  document.getElementById('pm-total').textContent = fmtMs(perf.total_ms);

  updateWaterfall(perf);

  document.getElementById('pd-paths').textContent = recallPaths;
  document.getElementById('pd-ctx').textContent = contextChars.toLocaleString();
  document.getElementById('pd-out').textContent = perf.output_chars.toLocaleString();
  document.getElementById('pd-str').textContent = feedback.strengthened;
  document.getElementById('pd-weak').textContent = feedback.weakened;

  document.getElementById('pd-mem').textContent = stats.memories;
  document.getElementById('pd-nodes').textContent = stats.nodes;
  document.getElementById('pd-edges').textContent = stats.edges;
  document.getElementById('pd-kbs').textContent = stats.knowledge_bases;
}

function makePerfStrip(perf, recallPaths, feedback) {
  const strip = document.createElement('div');
  strip.className = 'perf-strip';
  const tags = [
    ['recall', recallPaths + ' paths \u00b7 ' + fmtMs(perf.recall_ms)],
    ['speed', perf.tokens_per_sec + ' tok/s \u00b7 ' + perf.tokens + ' tokens'],
    ['time', 'ttft ' + fmtMs(perf.ttft_ms)],
    ['memory', 'mem+fb ' + fmtMs(perf.mem_add_ms + perf.feedback_ms)],
    ['feedback', '+' + feedback.strengthened + '/-' + feedback.weakened],
    ['time', 'total ' + fmtMs(perf.total_ms)],
  ];
  for (const [type, text] of tags) {
    const t = document.createElement('span');
    t.className = 'perf-tag perf-tag-' + type;
    t.textContent = text;
    strip.appendChild(t);
  }
  return strip;
}

async function refreshStats() {
  try {
    const res = await fetch('/api/stats');
    const s = await res.json();
    document.getElementById('stat-memories').textContent = s.memories;
    document.getElementById('stat-nodes').textContent = s.nodes;
    document.getElementById('stat-edges').textContent = s.edges;
    document.getElementById('stat-kbs').textContent = s.knowledge_bases;
  } catch(e) {}
}

async function handleCommand(text) {
  if (text === '/clear') {
    await fetch('/api/clear', { method: 'POST' });
    chatArea.innerHTML = '';
    addSystemMessage('Conversation history cleared (memory preserved)');
    return true;
  }
  if (text === '/stats') {
    const res = await fetch('/api/stats');
    const s = await res.json();
    addSystemMessage(
      'Memories: ' + s.memories + ' | Nodes: ' + s.nodes
      + ' | Edges: ' + s.edges + ' | KBs: ' + s.knowledge_bases
      + ' | Anchors: ' + s.anchors.join(', ')
    );
    return true;
  }
  if (text === '/perf') {
    perfPanel.classList.remove('collapsed');
    return true;
  }
  if (text.startsWith('/search ')) {
    const query = text.slice(8).trim();
    if (!query) return true;
    addSystemMessage('Searching memories: "' + query + '"');
    const res = await fetch('/api/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query }),
    });
    const data = await res.json();
    if (!data.results || data.results.length === 0) {
      addSystemMessage('No memories found.');
    } else {
      addSearchResults(data.results, data.search_ms);
    }
    return true;
  }
  if (text.startsWith('/kb add ')) {
    // Format: /kb add name|chunk1|chunk2|...
    const parts = text.slice(8).split('|').map(s => s.trim()).filter(Boolean);
    if (parts.length < 2) {
      addSystemMessage('Usage: /kb add name|text1|text2|...');
      return true;
    }
    const name = parts[0];
    const chunks = parts.slice(1).map(c => ({ content: c }));
    addSystemMessage('Adding knowledge base "' + name + '" with ' + chunks.length + ' chunks...');
    const res = await fetch('/api/knowledge/add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, chunks }),
    });
    const data = await res.json();
    addSystemMessage('KB added: ' + data.kb_id + ' (' + data.chunks + ' chunks, ' + data.add_ms + 'ms)');
    return true;
  }
  if (text.startsWith('/kb search ')) {
    const query = text.slice(11).trim();
    if (!query) return true;
    addSystemMessage('Searching knowledge: "' + query + '"');
    const res = await fetch('/api/knowledge/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query }),
    });
    const data = await res.json();
    if (!data.results || data.results.length === 0) {
      addSystemMessage('No knowledge found.');
    } else {
      for (const r of data.results) {
        const div = document.createElement('div');
        div.className = 'search-result';
        const meta = r.metadata && r.metadata.source ? ' [' + r.metadata.source + ']' : '';
        div.innerHTML =
          '<div class="search-header">'
          + '<span class="search-score">' + r.score.toFixed(3) + '</span>'
          + '<span class="search-category">knowledge</span>'
          + '<span class="search-time">' + data.search_ms + 'ms</span>'
          + '</div>'
          + '<div>' + escapeHtml(r.content) + escapeHtml(meta) + '</div>';
        chatArea.appendChild(div);
      }
      scrollBottom();
    }
    return true;
  }
  if (text.startsWith('/kb delete ')) {
    const kbId = text.slice(11).trim();
    if (!kbId) return true;
    const res = await fetch('/api/knowledge/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ kb_id: kbId }),
    });
    const data = await res.json();
    addSystemMessage('Knowledge base deleted: ' + data.kb_id);
    return true;
  }
  return false;
}

async function sendMessage() {
  const text = input.value.trim();
  if (!text || sending) return;

  input.value = '';
  removeEmpty();

  if (await handleCommand(text)) {
    await refreshStats();
    return;
  }

  sending = true;
  sendBtn.disabled = true;

  // User bubble
  const userGroup = document.createElement('div');
  userGroup.className = 'msg-group msg-group-user';
  const userLabel = document.createElement('div');
  userLabel.className = 'msg-label';
  userLabel.textContent = 'you';
  const userMsg = document.createElement('div');
  userMsg.className = 'msg msg-user';
  userMsg.textContent = text;
  userGroup.appendChild(userLabel);
  userGroup.appendChild(userMsg);
  chatArea.appendChild(userGroup);
  scrollBottom();

  // Assistant group
  const asstGroup = document.createElement('div');
  asstGroup.className = 'msg-group msg-group-assistant';
  const asstLabel = document.createElement('div');
  asstLabel.className = 'msg-label';
  asstLabel.textContent = 'assistant';

  const asstMsg = document.createElement('div');
  asstMsg.className = 'msg msg-assistant';
  const textSpan = document.createElement('span');
  const cursor = document.createElement('span');
  cursor.className = 'typing-cursor';
  asstMsg.appendChild(textSpan);
  asstMsg.appendChild(cursor);

  asstGroup.appendChild(asstLabel);
  asstGroup.appendChild(asstMsg);
  chatArea.appendChild(asstGroup);
  scrollBottom();

  let recallPaths = 0;
  let contextChars = 0;

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text }),
    });

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let firstToken = true;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        try {
          const evt = JSON.parse(line.slice(6));

          if (evt.type === 'recall') {
            recallPaths = evt.paths;
            contextChars = evt.context_chars || 0;
          }

          else if (evt.type === 'token') {
            textSpan.textContent += evt.content;
            scrollBottom();
          }

          else if (evt.type === 'done') {
            cursor.remove();
            const strip = makePerfStrip(evt.perf, recallPaths, evt.feedback);
            asstGroup.appendChild(strip);
            updatePerfPanel(evt.perf, evt.feedback, evt.stats, recallPaths, contextChars);
            scrollBottom();
          }
        } catch(e) {}
      }
    }

    // Safety: remove cursor if still present
    if (cursor.parentNode) cursor.remove();
    await refreshStats();

  } catch (err) {
    if (cursor.parentNode) cursor.remove();
    textSpan.textContent = 'Error: ' + err.message;
    if (!asstGroup.parentNode) {
      asstGroup.appendChild(asstLabel);
      asstGroup.appendChild(asstMsg);
      chatArea.appendChild(asstGroup);
    }
  }

  sending = false;
  sendBtn.disabled = false;
  input.focus();
}

sendBtn.addEventListener('click', sendMessage);
input.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

// --- Knowledge Base File Upload ---
const kbFileInput = document.getElementById('kb-file-input');
const kbUploadBtn = document.getElementById('kb-upload-btn');
const uploadProgress = document.getElementById('upload-progress');

kbFileInput.addEventListener('change', async () => {
  const files = kbFileInput.files;
  if (!files.length) return;

  kbUploadBtn.disabled = true;
  uploadProgress.classList.add('active');
  removeEmpty();

  for (const file of files) {
    uploadProgress.textContent = 'uploading ' + file.name + '...';
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('/api/knowledge/upload', { method: 'POST', body: formData });
      const data = await res.json();
      if (data.error) {
        addSystemMessage('Upload failed (' + file.name + '): ' + data.error);
      } else {
        addSystemMessage(
          'KB "' + data.name + '" added from ' + data.source
          + ' (' + data.chunks + ' chunks in ' + data.add_ms + 'ms)'
        );
      }
    } catch (err) {
      addSystemMessage('Upload error (' + file.name + '): ' + err.message);
    }
  }

  kbUploadBtn.disabled = false;
  uploadProgress.classList.remove('active');
  kbFileInput.value = '';
  await refreshStats();
});

// --- Boot health check ---
input.disabled = true;
sendBtn.disabled = true;
input.placeholder = 'Waiting for services to start...';

const bootBanner = addPhase('Booting up, have patience...', 'var(--accent-blue)');

async function checkHealth() {
  try {
    const res = await fetch('/api/health');
    if (res.ok) {
      const data = await res.json();
      if (data.status === 'ready') {
        bootBanner.remove();
        input.disabled = false;
        sendBtn.disabled = false;
        input.placeholder = 'Type a message... (/search, /kb search, /clear, /stats)';
        input.focus();
        refreshStats();
        return;
      }
    }
  } catch(e) {}
  setTimeout(checkHealth, 2000);
}
checkHealth();
</script>

</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML_PAGE


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
