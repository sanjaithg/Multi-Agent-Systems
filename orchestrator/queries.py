"""Read a query file. Accepts JSON (list or {"queries": [...]}), JSONL, or plain text (one question per line)."""
from __future__ import annotations

import json
from pathlib import Path

ID_KEYS = ("query_id", "id", "qid")
TEXT_KEYS = ("question", "query", "text", "prompt")
GRAPH_KEYS = ("graph_id", "graph")


def _normalise(item, index: int) -> dict:
    if isinstance(item, str):
        return {"query_id": f"q{index:02d}", "question": item.strip(), "graph_id": None}
    qid = next((item[k] for k in ID_KEYS if item.get(k) not in (None, "")), f"q{index:02d}")
    question = next((item[k] for k in TEXT_KEYS if isinstance(item.get(k), str)), None)
    if question is None:
        raise ValueError(f"query {qid!r} has no question text (looked for {TEXT_KEYS})")
    graph = next((item[k] for k in GRAPH_KEYS if isinstance(item.get(k), str)), None)
    return {"query_id": str(qid), "question": question.strip(), "graph_id": graph}


def load_queries(path: str | Path) -> list[dict]:
    text = Path(path).read_text(encoding="utf-8")
    stripped = text.strip()
    items: list = []
    if stripped.startswith("[") or stripped.startswith("{"):
        try:
            data = json.loads(stripped)
            if isinstance(data, dict):
                data = data.get("queries", data.get("questions", [data]))
            items = list(data)
        except ValueError:  # JSONL: several objects, one per line
            items = [json.loads(line) for line in stripped.splitlines() if line.strip()]
    else:
        items = [ln for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    return [_normalise(it, i) for i, it in enumerate(items, 1)]
