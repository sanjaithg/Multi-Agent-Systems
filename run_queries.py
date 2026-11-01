"""Answer a file of graph questions.

    python run_queries.py --queries queries/public_sample.json --out answers.json

Reads the API key from the LLM_API_KEY environment variable (or a .env file).
Writes one entry per question to --out and one trace per question to traces/<query_id>.jsonl.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from graphkit import GraphStore  # noqa: E402
from graphkit.llm import make_client, model_name  # noqa: E402
from graphkit.trace import Trace  # noqa: E402

from orchestrator.agent import Orchestrator  # noqa: E402
from orchestrator.queries import load_queries  # noqa: E402
from orchestrator.registry import ToolRegistry  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--queries", required=True, help="query file (JSON, JSONL or one question per line)")
    ap.add_argument("--out", default="answers.json", help="where to write answers (default answers.json)")
    ap.add_argument("--traces", default="traces", help="folder for per-question traces (default traces/)")
    ap.add_argument("--only", help="comma-separated query ids to run")
    args = ap.parse_args()

    queries = load_queries(args.queries)
    if args.only:
        wanted = set(args.only.split(","))
        queries = [q for q in queries if q["query_id"] in wanted]

    try:
        client = make_client()
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    registry = ToolRegistry()
    print(f"Loaded {len(registry)} tools from manifests; model {model_name()}; {len(queries)} questions.")
    out_path = Path(args.out)
    trace_dir = Path(args.traces)
    answers = []

    for q in queries:
        store = GraphStore()  # fresh store per question: subgraph ids never leak between questions
        agent = Orchestrator(client, registry, store)
        trace_path = trace_dir / f"{q['query_id']}.jsonl"
        trace = Trace(trace_path)
        t0 = time.time()
        try:
            r = agent.answer(q["question"], trace, graph_hint=q["graph_id"])
            entry = {"query_id": q["query_id"], "status": r.status, "answer_text": r.answer_text,
                     "answer": r.answer, "tools_used": r.tools_used}
        except Exception as exc:  # never lose the whole run to one question
            trace.error(f"{type(exc).__name__}: {exc}")
            entry = {"query_id": q["query_id"], "status": "error", "answer_text": f"ERROR: {exc}",
                     "answer": {"type": "text", "value": None}, "tools_used": []}
        entry["trace_file"] = trace_path.as_posix()
        answers.append(entry)
        out_path.write_text(json.dumps(answers, indent=2, ensure_ascii=False), encoding="utf-8")  # incremental
        print(f"[{q['query_id']}] {entry['status']:<20} {entry['answer']['value']!s:.60}  "
              f"({len(entry['tools_used'])} tools, {time.time() - t0:.1f}s)", flush=True)
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
