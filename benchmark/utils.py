"""Data download, parsing, and timing helpers for LOCOMO benchmark."""

import json
import re
import time
import urllib.request
from datetime import datetime
from pathlib import Path

from .config import BenchmarkConfig

LOCOMO_URL = (
    "https://raw.githubusercontent.com/snap-research/locomo/main/data/locomo10.json"
)


def download_locomo(config: BenchmarkConfig) -> Path:
    """Download locomo10.json if not already present."""
    dest = config.dataset_path
    if dest.exists():
        return dest
    config.data_dir.mkdir(parents=True, exist_ok=True)
    print(f"Downloading LOCOMO dataset to {dest}...")
    urllib.request.urlretrieve(LOCOMO_URL, dest)
    print(f"Downloaded ({dest.stat().st_size / 1024:.0f} KB)")
    return dest


def load_locomo(config: BenchmarkConfig) -> list[dict]:
    """Load and return parsed LOCOMO conversations."""
    path = download_locomo(config)
    with open(path) as f:
        data = json.load(f)
    return data


def parse_conversation_sessions(conversation: dict) -> list[dict]:
    """Extract ordered sessions from a LOCOMO conversation dict.

    The conversation dict has keys like:
        speaker_a, speaker_b,
        session_1_date_time, session_1 (list of turn dicts),
        session_2_date_time, session_2, ...

    Some sessions have only date_time (no turn data) — those are skipped.

    Returns list of:
        {session_id, date_time, timestamp, turns: [{speaker, text, dia_id}]}
    """
    conv_data = conversation.get("conversation", {})
    if not isinstance(conv_data, dict):
        return []

    sessions = []
    for i in range(1, 100):
        dt_key = f"session_{i}_date_time"
        s_key = f"session_{i}"

        if dt_key not in conv_data:
            break  # no more sessions

        date_time = conv_data.get(dt_key, "")
        timestamp = parse_timestamp(date_time)

        # Some sessions have date_time but no turn data
        raw_turns = conv_data.get(s_key)
        if not raw_turns or not isinstance(raw_turns, list):
            continue

        turns = []
        for turn in raw_turns:
            text = turn.get("text", "").strip()

            # Image turns: append caption to text
            if turn.get("blip_caption"):
                caption = turn["blip_caption"]
                if text:
                    text = f"{text} [shares image: {caption}]"
                else:
                    text = f"[shares image: {caption}]"

            if not text:
                continue

            turns.append({
                "speaker": turn.get("speaker", ""),
                "text": text,
                "dia_id": turn.get("dia_id", ""),
            })

        if turns:
            sessions.append({
                "session_id": i,
                "date_time": date_time,
                "timestamp": timestamp,
                "turns": turns,
            })

    return sessions


def parse_qa_questions(qa_list: list[dict], categories: list[int]) -> list[dict]:
    """Filter QA questions to specified categories and normalize.

    LOCOMO QA items have {question, answer, evidence, category} — no question_id,
    so we generate one from the index.

    Returns list of:
        {question_id, category, question, answer, evidence}
    """
    questions = []
    for idx, qa in enumerate(qa_list):
        cat = qa.get("category", 0)
        if isinstance(cat, str):
            try:
                cat = int(cat)
            except ValueError:
                continue
        if cat not in categories:
            continue

        questions.append({
            "question_id": qa.get("question_id", f"q_{idx}"),
            "category": cat,
            "question": str(qa.get("question", "")),
            "answer": str(qa.get("answer", "")),
            "evidence": qa.get("evidence", []),
        })

    return questions


def format_session_date(date_str: str) -> str:
    """Extract a clean date from LOCOMO date_time string.

    '1:56 pm on 8 May, 2023' → '8 May 2023'
    '10:00 am on 15 June, 2023' → '15 June 2023'
    """
    if not date_str:
        return ""
    m = re.search(r"(\d{1,2}\s+\w+),?\s+(\d{4})", date_str)
    if m:
        return f"{m.group(1)} {m.group(2)}"
    return date_str.strip()


def turns_to_chunks(
    turns: list[dict],
    session_date: str = "",
    chunk_size: int = 5,
    stride: int = 3,
) -> list[dict[str, str]]:
    """Convert LOCOMO turns to chunked messages for MemWire.add().

    Creates sliding-window chunks of consecutive turns with:
      - Session date prefix for temporal grounding
      - Speaker labels for attribution

    Returns list of {"role": "user", "content": chunk_text}.
    """
    if not turns:
        return []

    date_prefix = f"[Date: {session_date}]\n" if session_date else ""
    chunks = []

    for start in range(0, len(turns), stride):
        window = turns[start : start + chunk_size]
        if not window:
            break

        lines = []
        for turn in window:
            speaker = turn.get("speaker", "")
            text = turn.get("text", "").strip()
            if text:
                lines.append(f"{speaker}: {text}")

        if not lines:
            continue

        chunk_text = date_prefix + "\n".join(lines)
        chunks.append({"role": "user", "content": chunk_text})

    return chunks


def turns_to_messages(turns: list[dict]) -> list[dict[str, str]]:
    """Convert LOCOMO turns to message dicts for MemWire.add().

    First speaker maps to 'user', second to 'assistant'.
    """
    messages = []
    speakers_seen = []

    for turn in turns:
        speaker = turn.get("speaker", "")
        text = turn.get("text", "").strip()
        if not text:
            continue

        if speaker not in speakers_seen:
            speakers_seen.append(speaker)

        if speakers_seen and speaker == speakers_seen[0]:
            role = "user"
        else:
            role = "assistant"

        messages.append({"role": role, "content": text})

    return messages


def parse_timestamp(date_str: str) -> float:
    """Parse LOCOMO date string to Unix timestamp.

    Handles formats like:
        '1:56 pm on 8 May, 2023'
        '10:00 am on 15 June, 2023'
        '7 May 2023 10:00'
        '8 May, 2023'
    """
    if not date_str:
        return time.time()

    s = date_str.strip()

    # Handle "H:MM am/pm on D Month, Year" format
    m = re.match(
        r"(\d{1,2}:\d{2}\s*[ap]m)\s+on\s+(\d{1,2}\s+\w+,?\s+\d{4})", s, re.IGNORECASE
    )
    if m:
        time_part = m.group(1).strip()
        date_part = m.group(2).strip().replace(",", "")
        combined = f"{date_part} {time_part}"
        for fmt in ["%d %B %Y %I:%M %p", "%d %B %Y %I:%M%p"]:
            try:
                dt = datetime.strptime(combined, fmt)
                return dt.timestamp()
            except ValueError:
                continue

    # Fallback formats
    formats = [
        "%d %B, %Y",
        "%d %B %Y %H:%M",
        "%d %B %Y",
        "%B %d, %Y %H:%M",
        "%B %d, %Y",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(s, fmt)
            return dt.timestamp()
        except ValueError:
            continue

    return time.time()


class Timer:
    """Simple context-manager timer returning elapsed ms."""

    def __init__(self):
        self.elapsed_ms = 0.0

    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, *exc):
        self.elapsed_ms = (time.perf_counter() - self._start) * 1000
