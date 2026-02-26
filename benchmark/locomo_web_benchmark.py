"""FastAPI web dashboard for LOCOMO benchmark with live SSE progress."""

import asyncio
import json
import queue
import threading
import time

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

from .config import BenchmarkConfig
from .locomo_runner import BenchmarkRunner

# --- State ---
_benchmark_thread: threading.Thread | None = None
_progress_queue: queue.Queue = queue.Queue()
_status = {"running": False, "done": False, "aggregated": None}
_config: BenchmarkConfig | None = None


def _progress_callback(data: dict):
    """Thread-safe callback from BenchmarkRunner."""
    _progress_queue.put(data)
    if data.get("stage") == "done":
        _status["done"] = True
        _status["running"] = False
        _status["aggregated"] = data.get("aggregated")


def _run_benchmark():
    """Target for benchmark thread."""
    _status["running"] = True
    _status["done"] = False
    try:
        runner = BenchmarkRunner(config=_config, progress_callback=_progress_callback)
        runner.run()
    except Exception as e:
        import traceback
        traceback.print_exc()
        _progress_queue.put({"stage": "error", "message": str(e)})
        _status["running"] = False


app = FastAPI(title="LOCOMO Benchmark Dashboard")


@app.post("/api/start")
async def api_start(request: Request):
    global _benchmark_thread
    if _status["running"]:
        return JSONResponse({"error": "Benchmark already running"}, status_code=409)

    # Clear queue
    while not _progress_queue.empty():
        try:
            _progress_queue.get_nowait()
        except queue.Empty:
            break

    _status["done"] = False
    _status["aggregated"] = None
    _benchmark_thread = threading.Thread(target=_run_benchmark, daemon=True)
    _benchmark_thread.start()
    return JSONResponse({"status": "started"})


@app.post("/api/reset")
async def api_reset():
    if _status["running"]:
        return JSONResponse({"error": "Cannot reset while running"}, status_code=409)
    if _config and _config.progress_path.exists():
        _config.progress_path.unlink()
    _status["done"] = False
    _status["aggregated"] = None
    return JSONResponse({"status": "reset"})


@app.get("/api/progress")
async def api_progress():
    """SSE endpoint streaming progress events."""
    async def event_stream():
        while True:
            try:
                data = _progress_queue.get_nowait()
                yield f"data: {json.dumps(data)}\n\n"
                if data.get("stage") in ("done", "error"):
                    return
            except queue.Empty:
                if not _status["running"] and _progress_queue.empty():
                    if _status["done"]:
                        return
                yield f": heartbeat\n\n"
                await asyncio.sleep(0.2)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/api/status")
async def api_status():
    return JSONResponse({
        "running": _status["running"],
        "done": _status["done"],
        "has_results": _status["aggregated"] is not None,
    })


@app.get("/api/results")
async def api_results():
    if _status["aggregated"]:
        return JSONResponse(_status["aggregated"])
    if _config and _config.results_path.exists():
        return JSONResponse(json.loads(_config.results_path.read_text()))
    return JSONResponse({"error": "No results available"}, status_code=404)


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return HTMLResponse(HTML_PAGE)


# --- Dashboard HTML ---

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LOCOMO Benchmark — memwire</title>
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
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  background: var(--bg-primary);
  color: var(--text-primary);
  min-height: 100vh;
  overflow-y: auto;
}
.header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 24px; border-bottom: 1px solid var(--border);
  background: var(--bg-secondary); position: sticky; top: 0; z-index: 100;
}
.header h1 { font-size: 16px; font-weight: 600; }
.header h1 span { color: var(--accent-cyan); }
.header-actions { display: flex; gap: 10px; align-items: center; }
.btn {
  padding: 8px 16px; border: 1px solid var(--border-accent); border-radius: 6px;
  background: var(--bg-tertiary); color: var(--text-primary); cursor: pointer;
  font-family: inherit; font-size: 12px; transition: all 0.15s;
}
.btn:hover { border-color: var(--accent-cyan); color: var(--accent-cyan); }
.btn.primary { background: var(--accent-cyan); color: var(--bg-primary); border-color: var(--accent-cyan); font-weight: 600; }
.btn.primary:hover { opacity: 0.85; }
.btn:disabled { opacity: 0.4; cursor: not-allowed; }
.btn.danger { border-color: var(--accent-red); color: var(--accent-red); }
.btn.danger:hover { background: var(--accent-red); color: var(--bg-primary); }

.progress-section {
  padding: 16px 24px; background: var(--bg-secondary); border-bottom: 1px solid var(--border);
}
.progress-bar-container { height: 6px; background: var(--bg-tertiary); border-radius: 3px; overflow: hidden; margin-top: 8px; }
.progress-bar-fill { height: 100%; background: linear-gradient(90deg, var(--accent-cyan), var(--accent-blue)); border-radius: 3px; transition: width 0.3s; width: 0%; }
.progress-text { font-size: 12px; color: var(--text-secondary); display: flex; justify-content: space-between; }

.main { padding: 24px; display: flex; flex-direction: column; gap: 20px; }

.metrics-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.metric-card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px; padding: 16px; text-align: center; }
.metric-card .label { font-size: 11px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; }
.metric-card .value { font-size: 28px; font-weight: 700; margin-top: 4px; }
.metric-card .value.cyan { color: var(--accent-cyan); }
.metric-card .value.blue { color: var(--accent-blue); }
.metric-card .value.green { color: var(--accent-green); }
.metric-card .value.amber { color: var(--accent-amber); }

.categories-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.cat-card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px; padding: 14px; }
.cat-card .cat-name { font-size: 12px; color: var(--text-secondary); margin-bottom: 6px; }
.cat-card .cat-acc { font-size: 22px; font-weight: 700; color: var(--accent-cyan); }
.cat-card .cat-detail { font-size: 11px; color: var(--text-muted); margin-top: 4px; }

.comparison-section { background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px; padding: 16px; }
.comparison-section h3 { font-size: 13px; color: var(--text-secondary); margin-bottom: 14px; }
.bar-chart { display: flex; flex-direction: column; gap: 8px; }
.bar-row { display: flex; align-items: center; gap: 10px; }
.bar-label { width: 130px; font-size: 12px; text-align: right; color: var(--text-secondary); flex-shrink: 0; }
.bar-label.ours { color: var(--accent-cyan); font-weight: 600; }
.bar-track { flex: 1; height: 22px; background: var(--bg-tertiary); border-radius: 4px; overflow: hidden; position: relative; }
.bar-fill { height: 100%; border-radius: 4px; transition: width 0.5s; display: flex; align-items: center; padding-left: 8px; font-size: 11px; font-weight: 600; color: var(--bg-primary); }
.bar-fill.baseline { background: var(--border-accent); color: var(--text-secondary); }
.bar-fill.ours { background: linear-gradient(90deg, var(--accent-cyan), var(--accent-blue)); }

.latency-section { background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px; padding: 16px; }
.latency-section h3 { font-size: 13px; color: var(--text-secondary); margin-bottom: 12px; }
.latency-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.latency-item { text-align: center; }
.latency-item .ll { font-size: 11px; color: var(--text-muted); }
.latency-item .lv { font-size: 18px; font-weight: 600; color: var(--accent-amber); margin-top: 2px; }
.latency-item .lu { font-size: 10px; color: var(--text-muted); }

/* Log panel */
.log-section { background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }
.log-section .log-header { padding: 10px 16px; border-bottom: 1px solid var(--border); font-size: 13px; color: var(--text-secondary); }
.log-content { max-height: 180px; overflow-y: auto; padding: 8px 16px; font-size: 11px; line-height: 1.6; color: var(--text-muted); }
.log-content .log-line { white-space: nowrap; }
.log-content .log-ok { color: var(--accent-green); }
.log-content .log-err { color: var(--accent-red); }
.log-content .log-info { color: var(--accent-blue); }

/* Results table */
.results-section { background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }
.results-header { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; border-bottom: 1px solid var(--border); }
.results-header h3 { font-size: 13px; color: var(--text-secondary); }
.results-table-wrap { max-height: 400px; overflow-y: auto; }
table { width: 100%; border-collapse: collapse; font-size: 11px; }
th { background: var(--bg-tertiary); padding: 8px 10px; text-align: left; color: var(--text-secondary); position: sticky; top: 0; cursor: pointer; user-select: none; }
th:hover { color: var(--accent-cyan); }
td { padding: 6px 10px; border-top: 1px solid var(--border); color: var(--text-primary); max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
tr:hover td { background: var(--bg-tertiary); }
.correct { color: var(--accent-green); }
.wrong { color: var(--accent-red); }
.expanded-row td { white-space: normal; word-break: break-word; background: var(--bg-secondary); font-size: 11px; color: var(--text-secondary); padding: 10px; }

.status-badge { display: inline-block; padding: 2px 10px; border-radius: 10px; font-size: 11px; font-weight: 600; }
.status-badge.idle { background: var(--bg-tertiary); color: var(--text-muted); }
.status-badge.running { background: rgba(100, 255, 218, 0.15); color: var(--accent-cyan); }
.status-badge.done { background: rgba(129, 199, 132, 0.15); color: var(--accent-green); }
.status-badge.error { background: rgba(239, 69, 101, 0.15); color: var(--accent-red); }
</style>
</head>
<body>

<div class="header">
  <h1>LOCOMO Benchmark — <span>memwire</span></h1>
  <div class="header-actions">
    <span id="statusBadge" class="status-badge idle">IDLE</span>
    <button id="resetBtn" class="btn danger" onclick="resetProgress()">Reset</button>
    <button id="startBtn" class="btn primary" onclick="startBenchmark()">Start Benchmark</button>
    <button id="exportBtn" class="btn" onclick="exportResults()" disabled>Export JSON</button>
  </div>
</div>

<div class="progress-section">
  <div class="progress-text">
    <span id="progressLabel">Ready to start</span>
    <span id="progressPct">0%</span>
  </div>
  <div class="progress-bar-container">
    <div id="progressBar" class="progress-bar-fill"></div>
  </div>
</div>

<div class="main">
  <div class="metrics-row">
    <div class="metric-card"><div class="label">Overall Accuracy</div><div id="metricAcc" class="value cyan">—</div></div>
    <div class="metric-card"><div class="label">F1 Score</div><div id="metricF1" class="value blue">—</div></div>
    <div class="metric-card"><div class="label">BLEU-1</div><div id="metricBleu" class="value green">—</div></div>
    <div class="metric-card"><div class="label">Recall P50</div><div id="metricLatency" class="value amber">—</div></div>
  </div>

  <div class="categories-row">
    <div class="cat-card"><div class="cat-name">1 — Single-hop</div><div id="cat1Acc" class="cat-acc">—</div><div id="cat1Detail" class="cat-detail"></div></div>
    <div class="cat-card"><div class="cat-name">2 — Multi-hop</div><div id="cat2Acc" class="cat-acc">—</div><div id="cat2Detail" class="cat-detail"></div></div>
    <div class="cat-card"><div class="cat-name">3 — Temporal</div><div id="cat3Acc" class="cat-acc">—</div><div id="cat3Detail" class="cat-detail"></div></div>
    <div class="cat-card"><div class="cat-name">4 — Open-domain</div><div id="cat4Acc" class="cat-acc">—</div><div id="cat4Detail" class="cat-detail"></div></div>
  </div>

  <div class="comparison-section">
    <h3>Accuracy Comparison (LLM-as-Judge %)</h3>
    <div id="barChart" class="bar-chart"></div>
  </div>

  <div class="latency-section">
    <h3>Latency</h3>
    <div class="latency-grid">
      <div class="latency-item"><div class="ll">Recall P50</div><div id="latRecallP50" class="lv">—</div><div class="lu">ms</div></div>
      <div class="latency-item"><div class="ll">Recall P95</div><div id="latRecallP95" class="lv">—</div><div class="lu">ms</div></div>
      <div class="latency-item"><div class="ll">Recall Mean</div><div id="latRecallMean" class="lv">—</div><div class="lu">ms</div></div>
      <div class="latency-item"><div class="ll">Gen P50</div><div id="latGenP50" class="lv">—</div><div class="lu">ms</div></div>
      <div class="latency-item"><div class="ll">Gen P95</div><div id="latGenP95" class="lv">—</div><div class="lu">ms</div></div>
      <div class="latency-item"><div class="ll">Gen Mean</div><div id="latGenMean" class="lv">—</div><div class="lu">ms</div></div>
      <div class="latency-item"><div class="ll">Total P50</div><div id="latTotalP50" class="lv">—</div><div class="lu">ms</div></div>
      <div class="latency-item"><div class="ll">Total P95</div><div id="latTotalP95" class="lv">—</div><div class="lu">ms</div></div>
      <div class="latency-item"><div class="ll">Total Mean</div><div id="latTotalMean" class="lv">—</div><div class="lu">ms</div></div>
    </div>
  </div>

  <div class="log-section">
    <div class="log-header">Live Log</div>
    <div id="logContent" class="log-content"></div>
  </div>

  <div class="results-section">
    <div class="results-header">
      <h3>Individual Results (<span id="resultCount">0</span>)</h3>
    </div>
    <div class="results-table-wrap">
      <table>
        <thead><tr>
          <th onclick="sortTable(0)">Cat</th>
          <th onclick="sortTable(1)">Question</th>
          <th onclick="sortTable(2)">Gold</th>
          <th onclick="sortTable(3)">Predicted</th>
          <th onclick="sortTable(4)">F1</th>
          <th onclick="sortTable(5)">BLEU</th>
          <th onclick="sortTable(6)">Judge</th>
          <th onclick="sortTable(7)">Time</th>
        </tr></thead>
        <tbody id="resultsBody"></tbody>
      </table>
    </div>
  </div>
</div>

<script>
const baselines = BASELINES_PLACEHOLDER;
let allResults = [];
let liveStats = {correct: 0, total: 0, f1Sum: 0, bleuSum: 0};
let catStats = {};
let recallTimes = [];
let genTimes = [];
let totalTimes = [];
let sortCol = -1, sortAsc = true;
let startTime = null;
let totalQuestions = 0;

function startBenchmark() {
  document.getElementById('startBtn').disabled = true;
  document.getElementById('resetBtn').disabled = true;
  setBadge('running', 'RUNNING');
  allResults = [];
  liveStats = {correct: 0, total: 0, f1Sum: 0, bleuSum: 0};
  catStats = {};
  recallTimes = []; genTimes = []; totalTimes = [];
  document.getElementById('resultsBody').innerHTML = '';
  document.getElementById('logContent').innerHTML = '';
  startTime = Date.now();

  fetch('/api/start', {method: 'POST'}).then(() => {
    const es = new EventSource('/api/progress');
    es.onmessage = (event) => {
      const data = JSON.parse(event.data);
      handleEvent(data);
      if (data.stage === 'done' || data.stage === 'error') es.close();
    };
    es.onerror = () => { setTimeout(checkFinalStatus, 1000); es.close(); };
  });
}

function resetProgress() {
  if (confirm('Reset all progress? This deletes saved results.')) {
    fetch('/api/reset', {method: 'POST'}).then(() => {
      allResults = [];
      liveStats = {correct: 0, total: 0, f1Sum: 0, bleuSum: 0};
      catStats = {};
      recallTimes = []; genTimes = []; totalTimes = [];
      document.getElementById('resultsBody').innerHTML = '';
      document.getElementById('logContent').innerHTML = '';
      ['metricAcc','metricF1','metricBleu','metricLatency'].forEach(id => document.getElementById(id).textContent = '—');
      [1,2,3,4].forEach(c => { document.getElementById('cat'+c+'Acc').textContent = '—'; document.getElementById('cat'+c+'Detail').textContent = ''; });
      updateProgress(0, 0, 'Ready to start');
      setBadge('idle', 'IDLE');
      addLog('Progress reset', 'info');
    });
  }
}

function handleEvent(data) {
  if (data.stage === 'start') {
    totalQuestions = data.total_questions || 0;
    updateProgress(data.done || 0, totalQuestions, 'Starting...');
    addLog('Benchmark started: ' + totalQuestions + ' questions across ' + (data.total_conversations || '?') + ' conversations', 'info');
  }
  else if (data.stage === 'ingesting') {
    updateProgress(liveStats.total, totalQuestions, 'Ingesting conversation ' + data.conversation + '...');
    addLog('Ingesting conversation ' + data.conversation + ' (' + (data.conv_id || '') + ')...', 'info');
  }
  else if (data.stage === 'ingested') {
    const sec = data.ingest_ms ? (data.ingest_ms / 1000).toFixed(1) : '?';
    addLog('  Ingested: ' + data.memories + ' memories, ' + (data.nodes||0) + ' nodes, ' + (data.edges||0) + ' edges in ' + sec + 's', 'ok');
  }
  else if (data.stage === 'question') {
    totalQuestions = data.total_questions || totalQuestions;
    updateProgress(data.question_num - 1, totalQuestions, 'Cat' + data.category + ': ' + (data.question_text || ''));
  }
  else if (data.stage === 'result') {
    const r = data.result;
    allResults.push(r);
    liveStats.total++;
    liveStats.f1Sum += r.f1;
    liveStats.bleuSum += r.bleu1;
    if (r.judge_correct) liveStats.correct++;

    recallTimes.push(r.recall_ms);
    genTimes.push(r.generation_ms);
    totalTimes.push(r.total_ms);

    const c = r.category;
    if (!catStats[c]) catStats[c] = {correct: 0, total: 0, f1Sum: 0, bleuSum: 0};
    catStats[c].total++;
    catStats[c].f1Sum += r.f1;
    catStats[c].bleuSum += r.bleu1;
    if (r.judge_correct) catStats[c].correct++;

    totalQuestions = data.total_questions || totalQuestions;
    updateProgress(data.done, totalQuestions);
    updateLiveMetrics();
    addResultRow(r);
    addLog('[' + data.done + '/' + totalQuestions + '] Cat' + r.category + ' ' + (r.judge_correct ? 'OK' : 'WRONG') + ' F1=' + (r.f1*100).toFixed(1) + ' recall=' + Math.round(r.recall_ms) + 'ms | ' + r.question.substring(0,55), r.judge_correct ? 'ok' : 'err');
  }
  else if (data.stage === 'done') {
    setBadge('done', 'DONE');
    document.getElementById('startBtn').disabled = false;
    document.getElementById('resetBtn').disabled = false;
    document.getElementById('exportBtn').disabled = false;
    if (data.aggregated) updateFinalMetrics(data.aggregated);
    updateProgress(totalQuestions, totalQuestions, 'Complete!');
    addLog('Benchmark complete!', 'info');
  }
  else if (data.stage === 'error') {
    setBadge('error', 'ERROR');
    document.getElementById('startBtn').disabled = false;
    document.getElementById('resetBtn').disabled = false;
    updateProgress(0, 1, 'Error: ' + (data.message || 'Unknown'));
    addLog('ERROR: ' + (data.message || 'Unknown'), 'err');
  }
}

function addLog(text, cls) {
  const el = document.getElementById('logContent');
  const line = document.createElement('div');
  line.className = 'log-line' + (cls ? ' log-' + cls : '');
  const ts = new Date().toLocaleTimeString();
  line.textContent = ts + '  ' + text;
  el.appendChild(line);
  el.scrollTop = el.scrollHeight;
}

function updateProgress(done, total, label) {
  const pct = total > 0 ? Math.round(done / total * 100) : 0;
  document.getElementById('progressBar').style.width = pct + '%';
  document.getElementById('progressPct').textContent = pct + '%';
  if (label) document.getElementById('progressLabel').textContent = label;
  else {
    let eta = '';
    if (done > 0 && done < total && startTime) {
      const elapsed = (Date.now() - startTime) / 1000;
      const perQ = elapsed / done;
      const remaining = Math.round(perQ * (total - done));
      const mins = Math.floor(remaining / 60);
      const secs = remaining % 60;
      eta = ' — ETA ' + mins + 'm ' + secs + 's';
    }
    document.getElementById('progressLabel').textContent = done + '/' + total + eta;
  }
}

function percentile(arr, p) {
  if (!arr.length) return 0;
  const sorted = [...arr].sort((a,b) => a - b);
  const k = (sorted.length - 1) * p / 100;
  const f = Math.floor(k);
  const c = Math.min(f + 1, sorted.length - 1);
  return sorted[f] + (k - f) * (sorted[c] - sorted[f]);
}

function mean(arr) { return arr.length ? arr.reduce((a,b) => a+b, 0) / arr.length : 0; }

function updateLiveMetrics() {
  const t = liveStats.total;
  if (t === 0) return;
  const acc = (liveStats.correct / t * 100).toFixed(1);
  const f1 = (liveStats.f1Sum / t * 100).toFixed(1);
  const bleu = (liveStats.bleuSum / t * 100).toFixed(1);

  document.getElementById('metricAcc').textContent = acc + '%';
  document.getElementById('metricF1').textContent = f1 + '%';
  document.getElementById('metricBleu').textContent = bleu + '%';
  document.getElementById('resultCount').textContent = t;

  for (const c of [1,2,3,4]) {
    const cs = catStats[c];
    if (cs && cs.total > 0) {
      const cAcc = (cs.correct / cs.total * 100).toFixed(1);
      document.getElementById('cat' + c + 'Acc').textContent = cAcc + '%';
      document.getElementById('cat' + c + 'Detail').textContent =
        cs.correct + '/' + cs.total + ' correct, F1 ' + (cs.f1Sum / cs.total * 100).toFixed(1) + '%';
    }
  }

  // Live latency
  const rp50 = Math.round(percentile(recallTimes, 50));
  document.getElementById('metricLatency').textContent = rp50 + 'ms';
  document.getElementById('latRecallP50').textContent = rp50;
  document.getElementById('latRecallP95').textContent = Math.round(percentile(recallTimes, 95));
  document.getElementById('latRecallMean').textContent = Math.round(mean(recallTimes));
  document.getElementById('latGenP50').textContent = Math.round(percentile(genTimes, 50));
  document.getElementById('latGenP95').textContent = Math.round(percentile(genTimes, 95));
  document.getElementById('latGenMean').textContent = Math.round(mean(genTimes));
  document.getElementById('latTotalP50').textContent = Math.round(percentile(totalTimes, 50));
  document.getElementById('latTotalP95').textContent = Math.round(percentile(totalTimes, 95));
  document.getElementById('latTotalMean').textContent = Math.round(mean(totalTimes));

  updateComparisonChart(parseFloat(acc));
}

function updateFinalMetrics(agg) {
  const o = agg.overall || {};
  document.getElementById('metricAcc').textContent = (o.accuracy || 0) + '%';
  document.getElementById('metricF1').textContent = (o.f1 || 0) + '%';
  document.getElementById('metricBleu').textContent = (o.bleu1 || 0) + '%';

  const cats = agg.categories || {};
  for (const c of [1,2,3,4]) {
    const cd = cats[c] || cats[String(c)];
    if (cd) {
      document.getElementById('cat' + c + 'Acc').textContent = cd.accuracy + '%';
      document.getElementById('cat' + c + 'Detail').textContent =
        cd.count + ' questions, F1 ' + cd.f1 + '%, BLEU ' + cd.bleu1 + '%';
    }
  }

  const lat = agg.latency || {};
  document.getElementById('latRecallP50').textContent = lat.recall_p50 || '—';
  document.getElementById('latRecallP95').textContent = lat.recall_p95 || '—';
  document.getElementById('latRecallMean').textContent = lat.recall_mean || '—';
  document.getElementById('latGenP50').textContent = lat.generation_p50 || '—';
  document.getElementById('latGenP95').textContent = lat.generation_p95 || '—';
  document.getElementById('latGenMean').textContent = lat.generation_mean || '—';
  document.getElementById('latTotalP50').textContent = lat.total_p50 || '—';
  document.getElementById('latTotalP95').textContent = lat.total_p95 || '—';
  document.getElementById('latTotalMean').textContent = lat.total_mean || '—';
  document.getElementById('metricLatency').textContent = (lat.recall_p50 || '—') + 'ms';

  updateComparisonChart(o.accuracy || 0);
}

function updateComparisonChart(ourScore) {
  const entries = Object.entries(baselines).concat([['memwire', ourScore]]);
  entries.sort((a, b) => b[1] - a[1]);
  const maxVal = Math.max(...entries.map(e => e[1]), 100);
  let html = '';
  for (const [name, score] of entries) {
    const isOurs = name === 'memwire';
    const pct = (score / maxVal * 100).toFixed(1);
    html += '<div class="bar-row"><div class="bar-label' + (isOurs ? ' ours' : '') + '">' + name + '</div>' +
      '<div class="bar-track"><div class="bar-fill ' + (isOurs ? 'ours' : 'baseline') +
      '" style="width:' + pct + '%">' + score.toFixed(1) + '%</div></div></div>';
  }
  document.getElementById('barChart').innerHTML = html;
}

function addResultRow(r) {
  const tbody = document.getElementById('resultsBody');
  const tr = document.createElement('tr');
  tr.style.cursor = 'pointer';
  tr.onclick = () => toggleExpand(tr, r);
  const gold = String(r.gold);
  const pred = String(r.predicted);
  tr.innerHTML =
    '<td>' + r.category + '</td>' +
    '<td title="' + esc(r.question) + '">' + esc(r.question.substring(0, 60)) + '</td>' +
    '<td title="' + esc(gold) + '">' + esc(gold.substring(0, 40)) + '</td>' +
    '<td title="' + esc(pred) + '">' + esc(pred.substring(0, 40)) + '</td>' +
    '<td>' + (r.f1 * 100).toFixed(1) + '</td>' +
    '<td>' + (r.bleu1 * 100).toFixed(1) + '</td>' +
    '<td class="' + (r.judge_correct ? 'correct' : 'wrong') + '">' + (r.judge_correct ? 'OK' : 'WRONG') + '</td>' +
    '<td>' + Math.round(r.total_ms) + 'ms</td>';
  tbody.appendChild(tr);
}

function toggleExpand(tr, r) {
  const next = tr.nextElementSibling;
  if (next && next.classList.contains('expanded-row')) { next.remove(); return; }
  const exp = document.createElement('tr');
  exp.classList.add('expanded-row');
  exp.innerHTML = '<td colspan="8"><b>Q:</b> ' + esc(r.question) +
    '<br><b>Gold:</b> ' + esc(String(r.gold)) +
    '<br><b>Predicted:</b> ' + esc(String(r.predicted)) +
    '<br><b>Scores:</b> F1=' + (r.f1*100).toFixed(1) + '% BLEU=' + (r.bleu1*100).toFixed(1) +
    '% Judge=' + (r.judge_correct ? 'CORRECT' : 'WRONG') +
    '<br><b>Timing:</b> recall=' + Math.round(r.recall_ms) + 'ms gen=' + Math.round(r.generation_ms) +
    'ms eval=' + Math.round(r.eval_ms) + 'ms total=' + Math.round(r.total_ms) + 'ms</td>';
  tr.after(exp);
}

function sortTable(col) {
  if (sortCol === col) sortAsc = !sortAsc;
  else { sortCol = col; sortAsc = true; }
  const keys = ['category','question','gold','predicted','f1','bleu1','judge_correct','total_ms'];
  const key = keys[col];
  allResults.sort((a, b) => {
    let va = a[key], vb = b[key];
    if (typeof va === 'string') return sortAsc ? va.localeCompare(vb) : vb.localeCompare(va);
    if (typeof va === 'boolean') { va = va ? 1 : 0; vb = vb ? 1 : 0; }
    return sortAsc ? va - vb : vb - va;
  });
  const tbody = document.getElementById('resultsBody');
  tbody.innerHTML = '';
  allResults.forEach(r => addResultRow(r));
}

function exportResults() {
  fetch('/api/results').then(r => r.json()).then(data => {
    const blob = new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'locomo_results.json';
    a.click();
  });
}

function setBadge(cls, text) {
  const b = document.getElementById('statusBadge');
  b.className = 'status-badge ' + cls;
  b.textContent = text;
}

function esc(s) {
  if (!s) return '';
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function checkFinalStatus() {
  fetch('/api/status').then(r => r.json()).then(s => {
    if (s.done && s.has_results) {
      setBadge('done', 'DONE');
      document.getElementById('startBtn').disabled = false;
      document.getElementById('resetBtn').disabled = false;
      document.getElementById('exportBtn').disabled = false;
      fetch('/api/results').then(r => r.json()).then(data => {
        updateFinalMetrics(data);
        // Populate table from saved results
        if (data.individual_results) {
          allResults = data.individual_results;
          recallTimes = allResults.map(r => r.recall_ms);
          genTimes = allResults.map(r => r.generation_ms);
          totalTimes = allResults.map(r => r.total_ms);
          allResults.forEach(r => {
            liveStats.total++;
            liveStats.f1Sum += r.f1;
            liveStats.bleuSum += r.bleu1;
            if (r.judge_correct) liveStats.correct++;
            const c = r.category;
            if (!catStats[c]) catStats[c] = {correct: 0, total: 0, f1Sum: 0, bleuSum: 0};
            catStats[c].total++;
            catStats[c].f1Sum += r.f1;
            catStats[c].bleuSum += r.bleu1;
            if (r.judge_correct) catStats[c].correct++;
            addResultRow(r);
          });
          document.getElementById('resultCount').textContent = allResults.length;
          updateLiveMetrics();
        }
        updateProgress(data.total_questions || allResults.length, data.total_questions || allResults.length, 'Complete (loaded from previous run)');
        addLog('Loaded ' + allResults.length + ' results from previous run', 'info');
      });
    }
  }).catch(() => {});
}

// Initialize
updateComparisonChart(0);
checkFinalStatus();
</script>
</body>
</html>"""


def run_web_dashboard(config: BenchmarkConfig):
    """Launch the web dashboard."""
    global _config
    _config = config

    # Inject baselines into HTML template
    global HTML_PAGE
    HTML_PAGE = HTML_PAGE.replace(
        "BASELINES_PLACEHOLDER",
        json.dumps(config.baselines),
    )

    import uvicorn
    print(f"LOCOMO Benchmark Dashboard: http://localhost:{config.web_port}")
    uvicorn.run(app, host="0.0.0.0", port=config.web_port, log_level="warning")
