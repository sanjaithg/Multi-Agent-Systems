"""Score answers.json against an expected file using the course rules.

    python evaluate.py --answers answers.json --expected queries/sample_expected.json

Expected file: {query_id: {"status", "type", "value", "ordered"}} (or a list with a query_id field).
Rules: numbers within 0.1%; node lists as sets (in order when "ordered"); the right status for
ambiguous / unsupported questions; an answer is wrong if its trace does not support it.
"""
import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from orchestrator.grounding import Evidence, check_answer  # noqa: E402


def load_expected(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, list):
        data = {d["query_id"]: d for d in data}
    return data


def trace_evidence(trace_file):
    ev = Evidence()
    p = ROOT / trace_file if not Path(trace_file).is_absolute() else Path(trace_file)
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            rec = json.loads(line)
            if rec.get("type") == "tool_call":
                ev.add(rec["output"])
    return ev


def count_calls(trace_file):
    p = ROOT / trace_file if not Path(trace_file).is_absolute() else Path(trace_file)
    if not p.exists():
        return 0
    return sum(1 for line in p.read_text(encoding="utf-8").splitlines() if json.loads(line).get("type") == "tool_call")


def same(got, exp, ordered):
    t, g, e = exp["type"], got["value"], exp["value"]
    if t == "number":
        return isinstance(g, (int, float)) and not isinstance(g, bool) and math.isclose(g, e, rel_tol=1e-3, abs_tol=1e-9)
    if t in ("node_list", "path"):
        return isinstance(g, list) and (g == e if (ordered or t == "path") else set(g) == set(e) and len(g) == len(e))
    return g == e


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--answers", default="answers.json")
    ap.add_argument("--expected", required=True)
    args = ap.parse_args()
    expected = load_expected(args.expected)
    answers = {a["query_id"]: a for a in json.loads(Path(args.answers).read_text(encoding="utf-8"))}
    right, calls, rows = 0, [], []
    for qid, exp in expected.items():
        a = answers.get(qid)
        if a is None:
            rows.append((qid, "MISSING", "")); continue
        ok = a["status"] == exp["status"]
        why = "" if ok else f"status {a['status']} != {exp['status']}"
        if ok and exp["status"] == "answered":
            ok = a["answer"]["type"] == exp["type"] and same(a["answer"], exp, exp.get("ordered"))
            why = "" if ok else f"got {a['answer']} expected {exp['value']}"
            if ok:
                _, problem = check_answer(a["answer"]["type"], a["answer"]["value"], trace_evidence(a["trace_file"]))
                if problem:
                    ok, why = False, f"not supported by trace: {problem}"
        right += ok
        calls.append(count_calls(a["trace_file"]))
        rows.append((qid, "ok" if ok else "WRONG", why))
    for r in rows:
        print(f"{r[0]:6s} {r[1]:7s} {r[2][:150]}")
    print(f"\nAccuracy: {right}/{len(expected)} = {right / max(1, len(expected)):.1%}")
    if calls:
        print(f"Tool calls per question: mean {sum(calls) / len(calls):.2f}, max {max(calls)}")


if __name__ == "__main__":
    main()
