"""Choose one implementation per tool by testing every candidate.

    python curation/curate.py                 # test all candidates, write curation/report.{json,md}
    python curation/curate.py --apply         # also copy the winners into registry/tools/
    python curation/curate.py --only pagerank # test a single tool

Score (higher is better): contract validation (hard gate), NetworkX correctness
checks (main weight), determinism, graceful errors, and runtime on `airports`.
"""
from __future__ import annotations

import argparse
import json
import shutil
import signal
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from graphkit import GraphStore, load_tool  # noqa: E402
from graphkit.testing import to_networkx  # noqa: E402
from graphkit.validate import validate  # noqa: E402

import checks  # noqa: E402

CANDIDATES = ROOT / "curation" / "candidates"
REGISTRY = ROOT / "registry" / "tools"

# one slow-ish call per tool on airports, to measure runtime (canonical names)
TIMING = {
    "shortest_path_unweighted": dict(source="MAA", target="ANC"), "shortest_path_weighted": dict(source="MAA", target="ANC"),
    "reachability": dict(source="MAA", target="ANC"), "k_hop_neighborhood": dict(node="MAA", k=2),
    "ego_network": dict(node="MAA"), "personalized_pagerank": dict(node="MAA", seeds=["MAA"]),
    "max_flow_min_cut": dict(source="MAA", target="DEL"), "node_similarity": dict(a="MAA", b="DEL"),
    "node_embedding_similarity": dict(node="MAA"), "bipartite_matching": {}, "topological_sort": {},
    "girvan_newman": dict(num_communities=3),
}
TIMING_GRAPH = {"bipartite_matching": "projects", "topological_sort": "courses"}


def nx_cache(store):
    return {g: to_networkx(store.get(g)) for g in ("karate", "lesmis", "courses", "projects", "airports")}


class Timeout(Exception):
    pass


def _alarm(signum, frame):
    raise Timeout()


def evaluate_guarded(tool_dir: Path, store, ctx, seconds: int = 90) -> dict:
    """evaluate() with a wall-clock limit, so one pathological candidate cannot stall the run."""
    signal.signal(signal.SIGALRM, _alarm)
    signal.alarm(seconds)
    try:
        return evaluate(tool_dir, store, ctx)
    except Timeout:
        return {"tool": tool_dir.parent.name, "impl": tool_dir.name, "path": str(tool_dir.relative_to(ROOT)),
                "checks": [], "notes": [f"timed out after {seconds}s"], "validate_errors": [], "score": -2,
                "airports_seconds": seconds}
    finally:
        signal.alarm(0)


def evaluate(tool_dir: Path, store, ctx) -> dict:
    name = tool_dir.parent.name
    rec = {"tool": name, "impl": tool_dir.name, "path": str(tool_dir.relative_to(ROOT)), "checks": [], "notes": []}
    rep = validate(tool_dir)
    rec["validate_errors"] = rep.errors
    if rep.errors:
        rec["score"] = -1
        return rec
    try:
        tool = load_tool(tool_dir)
    except Exception as exc:
        rec.update(score=-1, validate_errors=[f"load failed: {exc}"])
        return rec
    P = checks.Probe(tool, store)
    try:
        t0 = time.time()
        results = checks.CHECKS[name](P, store, ctx)
        rec["check_seconds"] = round(time.time() - t0, 2)
    except Exception as exc:  # a check that blows up counts as a failure of the tool
        results = [("check crashed", False)]
        rec["notes"].append(f"check crashed: {type(exc).__name__}: {exc}")
    rec["checks"] = [{"name": n, "pass": bool(p)} for n, p in results]
    passed = sum(1 for _, p in results if p)
    rec["correct"] = passed / max(1, len(results))
    rec["dropped_params"] = sorted(P.dropped)
    # graceful errors
    bad = tool.call(store, graph_id="no_such_graph")
    bad_ok = isinstance(bad, dict) and bad.get("status") == "error" and bad.get("error")
    rec["graceful_error"] = bool(bad_ok)
    # runtime on the biggest graph
    gid = TIMING_GRAPH.get(name, "airports")
    t0 = time.time()
    o = P(graph_id=gid, **TIMING.get(name, {}))
    rec["airports_seconds"] = round(time.time() - t0, 2)
    rec["airports_status"] = o.get("status")
    rec["fast"] = rec["airports_seconds"] < 10
    score = 100 * rec["correct"] + (3 if bad_ok else 0) + (3 if rec["fast"] else 0) \
        - min(rec["airports_seconds"], 30) * 0.1 + (2 if o.get("status") == "ok" else 0)
    rec["score"] = round(score, 2)
    return rec


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--only")
    args = ap.parse_args()

    store = GraphStore()
    ctx = nx_cache(store)
    records, chosen = [], {}
    tools = sorted(p for p in CANDIDATES.iterdir() if p.is_dir() and (not args.only or p.name == args.only))
    for tdir in tools:
        if tdir.name not in checks.CHECKS:
            print(f"!! no checks for {tdir.name}")
        recs = []
        for idir in sorted(p for p in tdir.iterdir() if p.is_dir()):
            r = evaluate_guarded(idir, store, ctx)
            recs.append(r)
            fails = [c["name"] for c in r["checks"] if not c["pass"]]
            print(f"{tdir.name:30s} {idir.name}  score={r['score']:7.2f}  fails={fails or '-'} "
                  f"{r.get('validate_errors') or ''} t={r.get('airports_seconds')}", flush=True)
        recs.sort(key=lambda r: (-r["score"], len(r.get("dropped_params", [])), r["impl"]))
        if recs and recs[0]["score"] >= 0:
            chosen[tdir.name] = recs[0]["impl"]
        records.extend(recs)
        if recs:
            print(f"  -> chose {recs[0]['impl']}", flush=True)

    out = {"chosen": chosen, "records": records}
    (ROOT / "curation" / ("report.json" if not args.only else f"report_{args.only}.json")).write_text(
        json.dumps(out, indent=2), encoding="utf-8")
    if args.only:
        return
    write_markdown(out)
    if args.apply:
        shutil.rmtree(REGISTRY, ignore_errors=True)
        for tool, impl in chosen.items():
            dst = REGISTRY / tool / impl
            shutil.copytree(CANDIDATES / tool / impl, dst, ignore=shutil.ignore_patterns("__pycache__", "tests"))
        print(f"Copied {len(chosen)} tools into {REGISTRY}")


def write_markdown(out: dict) -> None:
    lines = ["# Tool curation report", "",
             "Every candidate was validated against the tool contract and tested against NetworkX references "
             "(`curation/checks.py`). One implementation per tool was kept.", "",
             "| tool | chosen | candidates | chosen score | failed checks of chosen | runner-up |", "|---|---|---|---|---|---|"]
    by_tool: dict[str, list] = {}
    for r in out["records"]:
        by_tool.setdefault(r["tool"], []).append(r)
    for tool, recs in by_tool.items():
        recs.sort(key=lambda r: (-r["score"], len(r.get("dropped_params", [])), r["impl"]))
        best = recs[0]
        fails = ", ".join(c["name"] for c in best["checks"] if not c["pass"]) or "-"
        ru = f"{recs[1]['impl']} ({recs[1]['score']})" if len(recs) > 1 else "-"
        lines.append(f"| {tool} | {best['impl']} | {len(recs)} | {best['score']} | {fails} | {ru} |")
    lines += ["", "## All candidates", "", "| tool | impl | score | correct | validate errors | failed checks |", "|---|---|---|---|---|---|"]
    for r in out["records"]:
        fails = ", ".join(c["name"] for c in r["checks"] if not c["pass"]) or "-"
        lines.append(f"| {r['tool']} | {r['impl']} | {r['score']} | {r.get('correct', '')} | "
                     f"{'; '.join(r['validate_errors'])[:80]} | {fails} |")
    (ROOT / "curation" / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
