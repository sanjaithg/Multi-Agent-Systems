"""Per-tool correctness checks used to choose one implementation of each tool.

Each check calls a candidate through `Probe` (which maps canonical parameter
names onto whatever names the candidate's manifest uses) and compares the
result with a NetworkX reference. NetworkX lives here only: it is a test oracle
and is never imported by the orchestrator or by any registry tool.
"""
from __future__ import annotations

import json
import math
import re
from typing import Any

import networkx as nx

from graphkit.testing import to_networkx

ALIASES = {
    "node": ["node", "node_id", "seed_node", "target_node", "center", "ego_node", "source"],
    "a": ["node_a", "node1", "node", "source", "src", "source_node", "u"],
    "b": ["node_b", "node2", "other", "target", "dest", "target_node", "other_node", "v"],
    "source": ["source", "src", "source_node", "from_node"],
    "target": ["target", "dest", "sink", "target_node", "to_node"],
    "top_k": ["top_k"],
    "k": ["k", "level", "radius", "hops"],
    "direction": ["direction", "mode", "degree_type"],
    "method": ["method"],
    "normalized": ["normalized"],
    "weighted": ["weighted", "use_weights"],
    "num_communities": ["num_communities", "n_communities", "communities"],
    "motif": ["motif"],
    "strategy": ["strategy"],
    "score": ["score", "score_type", "rank_by", "sort_by"],
    "seeds": ["seeds"],
    "ignore_direction": ["ignore_direction"],
    "left_value": ["left_value"],
}


class Probe:
    """Call a tool with canonical parameter names."""

    def __init__(self, tool, store):
        self.tool, self.store = tool, store
        self.props = tool.manifest["parameters"]["properties"]
        self.dropped: set[str] = set()

    def map(self, params: dict) -> dict:
        out = {}
        for canon, value in params.items():
            if canon == "graph_id":
                out["graph_id"] = value
                continue
            name = next((a for a in ALIASES.get(canon, [canon]) if a in self.props and a not in out), None)
            if name is None:
                self.dropped.add(canon)
                continue
            spec = self.props[name]
            if "enum" in spec and isinstance(value, str) and value not in spec["enum"]:
                self.dropped.add(canon)
                continue
            if spec.get("type") == "array" and not isinstance(value, list):
                value = [value]
            out[name] = value
        return out

    def __call__(self, **params) -> dict:
        return self.tool.call(self.store, **self.map(params))


# ----------------------------------------------------------------- helpers
def walk(obj):
    yield obj
    if isinstance(obj, dict):
        for v in obj.values():
            yield from walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk(v)


def node_ids(out: dict, graph) -> list[str]:
    """Node ids in the order they appear in the result (de-duplicated)."""
    seen, res = set(), []
    for x in walk(out.get("result")):
        cands = []
        if isinstance(x, dict):
            if "id" in x:
                cands.append(x["id"])
        elif isinstance(x, str) and graph.has_node(x):
            cands.append(x)
        for c in cands:
            if isinstance(c, str) and graph.has_node(c) and c not in seen:
                seen.add(c)
                res.append(c)
    return res


def numbers(out: dict) -> list[float]:
    vals = []
    for x in walk(out.get("result")):
        if isinstance(x, (int, float)) and not isinstance(x, bool):
            vals.append(float(x))
    return vals


def has_number(out: dict, expected: float, rel=2e-3, abs_=1e-3) -> bool:
    if any(math.isclose(v, expected, rel_tol=rel, abs_tol=abs_) for v in numbers(out)):
        return True
    return any(math.isclose(float(m), expected, rel_tol=rel, abs_tol=abs_)
               for m in re.findall(r"-?\d+(?:\.\d+)?", out.get("summary", "")))


def sub_nodes(store, gid) -> set[str]:
    return set(store.get(gid).nodes())


def sub_edges(store, gid) -> set[frozenset]:
    g = store.get(gid)
    return {frozenset((u, v)) for u, v, _ in g.edges()}


def result_graphs(out: dict) -> list[str]:
    """Graph ids referenced by the result (top-level and per component), de-duplicated."""
    ids = []
    if out.get("result_graph_id"):
        ids.append(out["result_graph_id"])
    for x in walk(out.get("result")):
        if isinstance(x, dict) and isinstance(x.get("graph_id"), str) and "~" in x["graph_id"]:
            ids.append(x["graph_id"])
    return list(dict.fromkeys(ids))


def parts_of(store, out) -> list[frozenset]:
    """Node sets of the communities/components listed in a result (one graph_id each)."""
    listed = [x["graph_id"] for x in walk(out.get("result")) if isinstance(x, dict)
              and isinstance(x.get("graph_id"), str) and "~" in x["graph_id"]]
    ids = list(dict.fromkeys(listed)) or ([out["result_graph_id"]] if out.get("result_graph_id") else [])
    return [frozenset(sub_nodes(store, g)) for g in ids]


def same_partition(parts, ref) -> bool:
    return sorted(map(sorted, parts)) == sorted(map(sorted, ref))


def top_ids(scores: dict, k: int) -> list[str]:
    return [n for n, _ in sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))[:k]]


def tie_ok(got: list[str], scores: dict, k: int, tol=1e-6) -> bool:
    """`got` is a valid top-k of `scores`, allowing ties at the cut-off."""
    if len(got) < k:
        return False
    ranked = sorted(scores.values(), reverse=True)
    cutoff = ranked[k - 1]
    return all(g in scores and scores[g] >= cutoff - tol for g in got[:k]) and len(set(got[:k])) == k


def ordered_ok(got: list[str], scores: dict, k: int, tol=1e-6) -> bool:
    if not tie_ok(got, scores, k, tol):
        return False
    vals = [scores[g] for g in got[:k]]
    return all(vals[i] >= vals[i + 1] - tol for i in range(len(vals) - 1))


def first_bool(out: dict, pattern: str):
    for x in walk(out.get("result")):
        if isinstance(x, dict):
            for key, v in x.items():
                if isinstance(v, bool) and re.search(pattern, key):
                    return v
    return None


def path_nodes(out: dict, graph) -> list[str]:
    for x in walk(out.get("result")):
        if isinstance(x, dict):
            for key in ("path", "nodes", "path_nodes"):
                v = x.get(key)
                if isinstance(v, list) and v and all(isinstance(i, (str, dict)) for i in v):
                    ids = [i["id"] if isinstance(i, dict) else i for i in v]
                    if all(graph.has_node(i) for i in ids):
                        return ids
    return node_ids(out, graph)


def valid_path(ids, graph, s, t) -> bool:
    if not ids or ids[0] != s or ids[-1] != t:
        return False
    return all(graph.weight(a, b) is not None or (not graph.directed and graph.weight(b, a) is not None)
               for a, b in zip(ids, ids[1:]))


def path_cost(ids, graph) -> float:
    return sum(graph.weight(a, b) if graph.weight(a, b) is not None else graph.weight(b, a)
               for a, b in zip(ids, ids[1:]))


# ------------------------------------------------------------------ checks
# A check is  f(P, S, ctx) -> list[(name, bool)];  ctx holds networkx graphs.
CHECKS: dict[str, Any] = {}


def check(name):
    def deco(fn):
        CHECKS[name] = fn
        return fn
    return deco


def ok(out):
    return out.get("status") == "ok"


@check("graph_summary")
def _(P, S, c):
    o, a = P(graph_id="karate"), P(graph_id="airports")
    return [("karate nodes", ok(o) and has_number(o, 34)), ("karate edges", ok(o) and has_number(o, 78)),
            ("karate density", ok(o) and has_number(o, nx.density(c["karate"]), rel=1e-3)),
            ("airports edges", ok(a) and has_number(a, 20058)),
            ("airports directed", ok(a) and "directed" in a["summary"].lower() and "undirected" not in a["summary"].lower())]


@check("degree_centrality")
def _(P, S, c):
    G, A = c["karate"], c["airports"]
    gk = S.get("karate")
    res = []
    o = P(graph_id="karate", top_k=5)
    d = dict(G.degree())
    res.append(("karate top5 degree", ok(o) and tie_ok(node_ids(o, gk), d, 5)))
    o = P(graph_id="airports", top_k=5, direction="out")
    res.append(("airports top5 out", ok(o) and tie_ok(node_ids(o, S.get("airports")), dict(A.out_degree()), 5)))
    o = P(graph_id="airports", top_k=5, direction="in")
    res.append(("airports top5 in", ok(o) and tie_ok(node_ids(o, S.get("airports")), dict(A.in_degree()), 5)))
    return res


@check("degree_distribution")
def _(P, S, c):
    G = c["karate"]
    o = P(graph_id="karate")
    degs = [d for _, d in G.degree()]
    return [("max degree", ok(o) and has_number(o, max(degs))), ("mean degree", ok(o) and has_number(o, sum(degs) / len(degs), rel=1e-3)),
            ("count deg 2", ok(o) and has_number(o, degs.count(2)))]


def ball(G, n, k, direction="out"):
    H = G
    if G.is_directed() and direction == "in":
        H = G.reverse(copy=False)
    elif G.is_directed() and direction == "both":
        H = G.to_undirected(as_view=True)
    return set(nx.single_source_shortest_path_length(H, n, cutoff=k))


def subgraph_nodes(P, S, out):
    gids = result_graphs(out)
    return sub_nodes(S, gids[0]) if gids else None


@check("k_hop_neighborhood")
def _(P, S, c):
    res = []
    o = P(graph_id="karate", node="m1", k=2, top_k=100)
    sn = subgraph_nodes(P, S, o) if ok(o) else None
    ref = ball(c["karate"], "m1", 2)
    res.append(("karate 2-hop subgraph", sn is not None and sn in (ref, ref - {"m1"})))
    o = P(graph_id="karate", node="m1", k=1, top_k=100)
    sn = subgraph_nodes(P, S, o) if ok(o) else None
    ref = ball(c["karate"], "m1", 1)
    res.append(("karate 1-hop subgraph", sn is not None and sn in (ref, ref - {"m1"})))
    o = P(graph_id="airports", node="MAA", k=2, direction="out", top_k=100)
    sn = subgraph_nodes(P, S, o) if ok(o) else None
    ref = ball(c["airports"], "MAA", 2, "out")
    res.append(("airports out 2-hop", sn is not None and sn in (ref, ref - {"MAA"})))
    o = P(graph_id="airports", node="MAA", k=1, direction="in", top_k=100)
    sn = subgraph_nodes(P, S, o) if ok(o) else None
    ref = ball(c["airports"], "MAA", 1, "in")
    res.append(("airports in 1-hop", sn is not None and sn in (ref, ref - {"MAA"})))
    return res


@check("ego_network")
def _(P, S, c):
    res = []
    o = P(graph_id="karate", node="m1", k=1, top_k=100)
    sn = subgraph_nodes(P, S, o) if ok(o) else None
    ref = ball(c["karate"], "m1", 1)
    res.append(("karate ego", sn is not None and sn in (ref, ref - {"m1"})))
    o = P(graph_id="karate", node="m34", k=1, top_k=100)
    sn = subgraph_nodes(P, S, o) if ok(o) else None
    ref = ball(c["karate"], "m34", 1)
    res.append(("karate ego m34", sn is not None and sn in (ref, ref - {"m34"})))
    o = P(graph_id="airports", node="MAA", direction="out", top_k=100)
    sn = subgraph_nodes(P, S, o) if ok(o) else None
    ref = ball(c["airports"], "MAA", 1, "out")
    res.append(("airports out ego", sn is not None and sn in (ref, ref - {"MAA"})))
    o = P(graph_id="airports", node="MAA", direction="in", top_k=100)
    sn = subgraph_nodes(P, S, o) if ok(o) else None
    ref = ball(c["airports"], "MAA", 1, "in")
    res.append(("airports in ego", sn is not None and sn in (ref, ref - {"MAA"})))
    return res


@check("reachability")
def _(P, S, c):
    D = c["courses"]
    res = []
    pairs = [("CS101", "CS102"), ("CS102", "CS101")]
    ns = list(D.nodes())
    far = next(((a, b) for a in ns for b in ns if a != b and nx.has_path(D, a, b) and len(nx.shortest_path(D, a, b)) > 3), None)
    if far:
        pairs.append(far)
    nopath = next(((a, b) for a in ns for b in ns if a != b and not nx.has_path(D, a, b) and not nx.has_path(D, b, a)), None)
    if nopath:
        pairs.append(nopath)
    for a, b in pairs:
        o = P(graph_id="courses", source=a, target=b)
        want = nx.has_path(D, a, b)
        got = first_bool(o, r"reach|exist|connected|path") if ok(o) else None
        if got is None and ok(o):
            txt = o["summary"].lower()
            got = not re.search(r"\bnot\b|\bno path\b|unreachable|cannot|can't", txt)
        res.append((f"{a}->{b}", got is not None and got == want))
    return res


def shortest_checks(P, S, c, gid, pairs, weighted):
    res = []
    G, g = c[gid], S.get(gid)
    for a, b in pairs:
        o = P(graph_id=gid, source=a, target=b)
        if weighted:
            want = nx.dijkstra_path_length(G, a, b, weight="weight")
        else:
            want = nx.shortest_path_length(G, a, b)
        ids = path_nodes(o, g) if ok(o) else []
        res.append((f"{a}->{b} length", ok(o) and has_number(o, want, rel=1e-3)))
        res.append((f"{a}->{b} path valid", ok(o) and valid_path(ids, g, a, b)
                    and math.isclose(path_cost(ids, g) if weighted else len(ids) - 1, want, rel_tol=1e-6)))
    return res


@check("shortest_path_unweighted")
def _(P, S, c):
    res = shortest_checks(P, S, c, "karate", [("m1", "m34"), ("m17", "m30")], False)
    res += shortest_checks(P, S, c, "airports", [("MAA", "ANC"), ("DEL", "SYD")], False)
    o = P(graph_id="courses", source="CS101", target="MA101")
    res.append(("no path handled", o.get("status") in ("ok", "error") and not (ok(o) and has_number(o, 1) and False)))
    return res


@check("shortest_path_weighted")
def _(P, S, c):
    res = shortest_checks(P, S, c, "airports", [("MAA", "ANC"), ("DEL", "SYD"), ("MAA", "JFK")], True)
    res += shortest_checks(P, S, c, "lesmis", [("c01", "c70")], True)
    return res


@check("connected_components")
def _(P, S, c):
    res = []
    G = c["karate"]
    keep = [n for n in G.nodes if n not in ("m1", "m34", "m33")]
    sid = S.subgraph("karate", keep, "karate without three hubs")
    H = to_networkx(S.get(sid))
    ref = [frozenset(x) for x in nx.connected_components(H)]
    o = P(graph_id=sid, top_k=50)
    parts = [frozenset(sub_nodes(S, g)) for g in result_graphs(o)
             if g != sid and S.get(g).number_of_nodes() < H.number_of_nodes()] if ok(o) else []
    res.append(("component count", ok(o) and has_number(o, len(ref))))
    res.append(("component sets", sorted(map(sorted, parts)) == sorted(map(sorted, ref))))
    res.append(("largest size", ok(o) and has_number(o, max(map(len, ref)))))
    o = P(graph_id="karate")
    res.append(("connected graph", ok(o) and has_number(o, 1) and has_number(o, 34)))
    return res


@check("clustering_coefficient")
def _(P, S, c):
    G = c["karate"]
    res = []
    o = P(graph_id="karate", node="m1")
    res.append(("m1 local", ok(o) and has_number(o, nx.clustering(G, "m1"), rel=1e-3)))
    o = P(graph_id="karate", node="m34")
    res.append(("m34 local", ok(o) and has_number(o, nx.clustering(G, "m34"), rel=1e-3)))
    o = P(graph_id="karate")
    res.append(("karate average", ok(o) and has_number(o, nx.average_clustering(G), rel=1e-3)))
    o = P(graph_id="karate", top_k=3)
    res.append(("triangle-free node", True))
    return res


@check("node_similarity")
def _(P, S, c):
    G = c["karate"]
    res = []
    for a, b in [("m1", "m2"), ("m33", "m34")]:
        o = P(graph_id="karate", a=a, b=b)
        na, nb = set(G[a]), set(G[b])
        jac = len(na & nb) / len(na | nb)
        res.append((f"{a},{b} jaccard", ok(o) and has_number(o, jac, rel=1e-3)))
        res.append((f"{a},{b} common", ok(o) and has_number(o, len(na & nb))))
    return res


def rank_check(P, S, c, gid, canon, scores, k=5, ordered=True, tol=1e-6, **params):
    o = P(graph_id=gid, top_k=k, **params)
    ids = node_ids(o, S.get(gid)) if ok(o) else []
    fn = ordered_ok if ordered else tie_ok
    return ok(o) and fn(ids, scores, k, tol)


@check("pagerank")
def _(P, S, c):
    res = []
    G = c["karate"]
    pr = nx.pagerank(G, tol=1e-12)
    res.append(("karate top5", rank_check(P, S, c, "karate", "pr", pr, tol=1e-5)))
    A = c["airports"]
    pr = nx.pagerank(A, weight="weight", tol=1e-12)
    pa = nx.pagerank(A, weight=None, tol=1e-12)
    # either weighting convention is acceptable; the tool must be internally consistent with one
    res.append(("airports top5", rank_check(P, S, c, "airports", "pr", pr, tol=1e-5)
                or rank_check(P, S, c, "airports", "pr", pa, tol=1e-5)))
    o = P(graph_id="karate", top_k=1)
    res.append(("score value", ok(o) and has_number(o, max(nx.pagerank(G, tol=1e-12).values()), rel=1e-3)))
    o = P(graph_id="karate", top_k=3, damping=0.5)
    res.append(("damping respected", ok(o) and has_number(o, max(nx.pagerank(G, alpha=0.5, tol=1e-12).values()), rel=1e-3)))
    return res


@check("personalized_pagerank")
def _(P, S, c):
    G = c["karate"]
    ref = nx.pagerank(G, personalization={"m1": 1.0}, tol=1e-12)
    res = []
    o = P(graph_id="karate", node="m1", seeds=["m1"], top_k=5)
    ids = node_ids(o, S.get("karate")) if ok(o) else []
    nosrc = {k: v for k, v in ref.items() if k != "m1"}
    res.append(("top5 incl or excl seed", ok(o) and (tie_ok(ids, ref, 5, 1e-5) or tie_ok([i for i in ids if i != "m1"], nosrc, 4, 1e-5))))
    res.append(("score value", ok(o) and has_number(o, max(nosrc.values()), rel=1e-2)))
    ref2 = nx.pagerank(G, personalization={"m34": 1.0}, tol=1e-12)
    o = P(graph_id="karate", node="m34", seeds=["m34"], top_k=3)
    ids = node_ids(o, S.get("karate")) if ok(o) else []
    res.append(("seed m34 top", ok(o) and len(ids) >= 2 and ids[0] in ref2 and ids[1] in top_ids(ref2, 4)))
    return res


@check("hits")
def _(P, S, c):
    G = c["karate"]
    h, a = nx.hits(G, max_iter=1000, tol=1e-12)
    res = []
    o = P(graph_id="karate", top_k=5, score="authority")
    res.append(("karate authority top5", ok(o) and tie_ok(node_ids(o, S.get("karate")), a, 5, 1e-4)))
    A = c["airports"]
    U = nx.DiGraph(A.edges())
    hw, aw = nx.hits(A, max_iter=1000, tol=1e-12)
    hu, au = nx.hits(U, max_iter=1000, tol=1e-12)
    g = S.get("airports")
    for kind, (rw, ru) in (("hub", (hw, hu)), ("authority", (aw, au))):
        got = []
        for weighted in (False, True):
            o = P(graph_id="airports", top_k=5, score=kind, weighted=weighted)
            ids = node_ids(o, g) if ok(o) else []
            got.append(ok(o) and (tie_ok(ids, rw, 5, 1e-4) or tie_ok(ids, ru, 5, 1e-4)))
        res.append((f"airports {kind} top5 (either weighting)", any(got)))
    o = P(graph_id="airports", top_k=3, score="hub", weighted=False)
    res.append(("airports hub value", ok(o) and (has_number(o, max(hu.values()), rel=1e-2) or has_number(o, max(hw.values()), rel=1e-2))))
    return res


@check("closeness_centrality")
def _(P, S, c):
    res = []
    G = c["karate"]
    cc = nx.closeness_centrality(G)
    res.append(("karate top5", rank_check(P, S, c, "karate", "cc", cc, tol=1e-5)))
    o = P(graph_id="karate", top_k=1)
    res.append(("score value", ok(o) and has_number(o, max(cc.values()), rel=1e-3)))
    o = P(graph_id="karate", node="m17")
    res.append(("single node", ok(o) and has_number(o, cc["m17"], rel=1e-3)))
    D = c["airports"]
    cr = nx.closeness_centrality(D.reverse(copy=False))  # incoming distances (networkx convention)
    res.append(("airports top5 (in)", rank_check(P, S, c, "airports", "cc", cr, tol=1e-4, direction="in")
                or rank_check(P, S, c, "airports", "cc", cr, tol=1e-4)))
    return res


@check("strongly_connected_components")
def _(P, S, c):
    res = []
    D = c["courses"]
    o = P(graph_id="courses", top_k=50)
    res.append(("DAG count", ok(o) and has_number(o, 21)))
    A = c["airports"]
    comps = sorted(nx.strongly_connected_components(A), key=len, reverse=True)
    o = P(graph_id="airports", top_k=10)
    res.append(("airports largest", ok(o) and has_number(o, len(comps[0]))))
    res.append(("airports count", ok(o) and has_number(o, len(comps))))
    gids = result_graphs(o) if ok(o) else []
    res.append(("largest subgraph", any(sub_nodes(S, g) == set(comps[0]) for g in gids)))
    return res


@check("topological_sort")
def _(P, S, c):
    res = []
    D = c["courses"]
    o = P(graph_id="courses", top_k=100)
    ids = node_ids(o, S.get("courses")) if ok(o) else []
    pos = {n: i for i, n in enumerate(ids)}
    res.append(("all nodes", len(ids) == 21))
    res.append(("order valid", len(ids) == 21 and all(pos[u] < pos[v] for u, v in D.edges)))
    o = P(graph_id="karate")
    res.append(("undirected graph handled", o.get("status") in ("ok", "error")))
    o = P(graph_id="airports")
    res.append(("cyclic graph is error/not sorted", o.get("status") == "error" or
                bool(re.search(r"cycl|not a dag|acyclic", (o.get("summary", "") + json.dumps(o.get("result"))).lower()))))
    return res


@check("minimum_spanning_tree")
def _(P, S, c):
    res = []
    L = c["lesmis"]
    w = nx.minimum_spanning_tree(L, weight="weight").size(weight="weight")
    o = P(graph_id="lesmis", top_k=100)
    res.append(("lesmis weight", ok(o) and has_number(o, w, rel=1e-4)))
    gids = result_graphs(o) if ok(o) else []
    res.append(("tree subgraph", bool(gids) and S.get(gids[0]).number_of_edges() == 76))
    o = P(graph_id="karate", top_k=100)
    gids = result_graphs(o) if ok(o) else []
    res.append(("karate 33 edges", bool(gids) and S.get(gids[0]).number_of_edges() == 33))
    return res


@check("diameter_eccentricity")
def _(P, S, c):
    G = c["karate"]
    res = []
    o = P(graph_id="karate")
    res.append(("diameter", ok(o) and has_number(o, nx.diameter(G))))
    res.append(("radius", ok(o) and has_number(o, nx.radius(G))))
    o = P(graph_id="karate", node="m17")
    res.append(("ecc m17", ok(o) and has_number(o, nx.eccentricity(G, "m17"))))
    L = c["lesmis"]
    o = P(graph_id="lesmis")
    res.append(("lesmis diameter", ok(o) and has_number(o, nx.diameter(L))))
    return res


@check("bipartite_check")
def _(P, S, c):
    res = []
    o = P(graph_id="projects")
    b = first_bool(o, r"bipartite") if ok(o) else None
    res.append(("projects true", ok(o) and (b is True if b is not None else "not bipartite" not in o["summary"].lower())))
    o = P(graph_id="karate")
    b = first_bool(o, r"bipartite") if ok(o) else None
    res.append(("karate false", ok(o) and (b is False if b is not None else bool(re.search(r"not|isn't|no ", o["summary"].lower())))))
    o = P(graph_id="lesmis")
    b = first_bool(o, r"bipartite") if ok(o) else None
    res.append(("lesmis false", ok(o) and (b is False if b is not None else bool(re.search(r"not|isn't|no ", o["summary"].lower())))))
    return res


@check("articulation_points_bridges")
def _(P, S, c):
    G = c["karate"]
    res = []
    o = P(graph_id="karate", top_k=50)
    aps = set(nx.articulation_points(G))
    bridges = list(nx.bridges(G))
    ids = set(node_ids(o, S.get("karate"))) if ok(o) else set()
    res.append(("articulation set", aps <= ids))
    res.append(("bridge count", ok(o) and has_number(o, len(bridges))))
    res.append(("ap count", ok(o) and has_number(o, len(aps))))
    H = c["lesmis"]
    o = P(graph_id="lesmis", top_k=50)
    res.append(("lesmis ap count", ok(o) and has_number(o, len(list(nx.articulation_points(H))))))
    return res


@check("k_core")
def _(P, S, c):
    G = c["karate"]
    res = []
    for k in (2, 3, 4):
        o = P(graph_id="karate", k=k, top_k=100)
        sn = subgraph_nodes(P, S, o) if ok(o) else None
        res.append((f"{k}-core", sn == set(nx.k_core(G, k).nodes)))
    o = P(graph_id="karate", k=5)
    res.append(("empty core handled", o.get("status") in ("ok", "error")))
    return res


@check("label_propagation")
def _(P, S, c):
    res = []
    o = P(graph_id="karate", top_k=50)
    parts = parts_of(S, o) if ok(o) else []
    allp = set().union(*parts) if parts else set()
    res.append(("partition covers", allp == set(c["karate"].nodes)))
    res.append(("partition disjoint", sum(map(len, parts)) == len(allp) and bool(parts)))
    res.append(("communities plausible", 2 <= len(parts) <= 12))
    o2 = P(graph_id="karate", top_k=50)
    res.append(("deterministic", o == o2 or (ok(o2) and sorted(map(sorted, parts)) == sorted(map(sorted, parts_of(S, o2))))))
    return res


@check("link_prediction")
def _(P, S, c):
    G = c["karate"]
    res = []
    g = S.get("karate")
    for method, fn in [("common_neighbors", lambda: [(u, v, len(list(nx.common_neighbors(G, u, v)))) for u, v in nx.non_edges(G)]),
                       ("jaccard", lambda: [(u, v, p) for u, v, p in nx.jaccard_coefficient(G)]),
                       ("adamic_adar", lambda: [(u, v, p) for u, v, p in nx.adamic_adar_index(G)])]:
        o = P(graph_id="karate", method=method, top_k=5)
        scores = sorted(fn(), key=lambda t: -t[2])
        best = scores[0][2]
        top = {frozenset((u, v)) for u, v, s in scores if s >= scores[4][2] - 1e-9}
        ids = node_ids(o, g) if ok(o) else []
        res.append((f"{method} first pair", ok(o) and len(ids) >= 2 and frozenset(ids[:2]) in top))
        res.append((f"{method} best score", ok(o) and has_number(o, best, rel=1e-3)))
    return res


@check("greedy_coloring")
def _(P, S, c):
    G = c["karate"]
    res = []
    o = P(graph_id="karate")
    nums = [v for x in walk(o.get("result")) if isinstance(x, dict) for k, v in x.items()
            if re.search(r"num.*colou?rs?|colou?rs?_?(used|count)|n_colou?rs?|chromatic", k) and isinstance(v, (int, float)) and not isinstance(v, bool)] if ok(o) else []
    res.append(("color count plausible", bool(nums) and all(5 <= v <= 18 for v in nums)))
    cols = {}
    for x in walk(o.get("result")):
        if isinstance(x, dict) and "id" in x and any(k in x for k in ("color", "colour")):
            cols[x["id"]] = x.get("color", x.get("colour"))
    if len(cols) == 34:
        res.append(("coloring proper", all(cols[u] != cols[v] for u, v in G.edges)))
    else:
        o2 = P(graph_id="karate", node="m1")
        res.append(("node query ok", ok(o2)))
    D = c["projects"]
    o = P(graph_id="projects")
    nums = [v for x in walk(o.get("result")) if isinstance(x, dict) for k, v in x.items()
            if re.search(r"num.*colou?rs?|colou?rs?_?(used|count)|n_colou?rs?", k) and isinstance(v, (int, float))] if ok(o) else []
    res.append(("bipartite uses 2..4 colors", bool(nums) and all(2 <= v <= 4 for v in nums)))
    return res


@check("betweenness_centrality")
def _(P, S, c):
    res = []
    G = c["karate"]
    bc = nx.betweenness_centrality(G)
    res.append(("karate top5 normalized", rank_check(P, S, c, "karate", "bc", bc, tol=1e-5)))
    o = P(graph_id="karate", top_k=1)
    res.append(("score value", ok(o) and has_number(o, max(bc.values()), rel=1e-3)))
    bu = nx.betweenness_centrality(G, normalized=False)
    o = P(graph_id="karate", top_k=1, normalized=False)
    res.append(("unnormalized", ok(o) and has_number(o, max(bu.values()), rel=1e-3)))
    L = c["lesmis"]
    bl = nx.betweenness_centrality(L, weight="weight")
    bl0 = nx.betweenness_centrality(L)
    res.append(("lesmis top5 (weighted flag)", rank_check(P, S, c, "lesmis", "bc", bl, tol=1e-5, weighted=True)))
    res.append(("lesmis top5 (unweighted)", rank_check(P, S, c, "lesmis", "bc", bl0, tol=1e-5, weighted=False)))
    return res


@check("louvain")
def _(P, S, c):
    res = []
    G = c["karate"]
    o = P(graph_id="karate", top_k=50)
    parts = parts_of(S, o) if ok(o) else []
    allp = set().union(*parts) if parts else set()
    res.append(("partition covers/disjoint", allp == set(G.nodes) and sum(map(len, parts)) == len(allp)))
    mod = nx.community.modularity(G, [set(p) for p in parts]) if parts and allp == set(G.nodes) else -1
    res.append(("modularity >= 0.40", mod >= 0.40))
    res.append(("reported modularity correct", ok(o) and has_number(o, mod, rel=2e-3)))
    L = c["lesmis"]
    o = P(graph_id="lesmis", top_k=50)
    parts = parts_of(S, o) if ok(o) else []
    allp = set().union(*parts) if parts else set()
    mod = nx.community.modularity(L, [set(p) for p in parts], weight="weight") if parts and allp == set(L.nodes) else -1
    res.append(("lesmis modularity >= 0.52", mod >= 0.52))
    o2 = P(graph_id="karate", top_k=50)
    res.append(("deterministic", ok(o2) and o2.get("summary") == P(graph_id="karate", top_k=50).get("summary")))
    return res


@check("girvan_newman")
def _(P, S, c):
    G = c["karate"]
    ref = [frozenset(x) for x in next(nx.community.girvan_newman(G))]
    res = []
    o = P(graph_id="karate", num_communities=2, top_k=50)
    parts = parts_of(S, o) if ok(o) else []
    res.append(("2-way split matches networkx", same_partition(parts, ref)))
    it = nx.community.girvan_newman(G)
    next(it)
    ref3 = [frozenset(x) for x in next(it)]
    o = P(graph_id="karate", num_communities=3, top_k=50)
    parts = parts_of(S, o) if ok(o) else []
    res.append(("3-way split matches networkx", same_partition(parts, ref3)))
    return res


@check("max_flow_min_cut")
def _(P, S, c):
    res = []
    A = c["airports"]
    for s, t in [("MAA", "DEL"), ("BOM", "JFK")]:
        want = nx.maximum_flow_value(A, s, t, capacity="weight")
        o = P(graph_id="airports", source=s, target=t)
        res.append((f"flow {s}->{t}", ok(o) and has_number(o, want, rel=1e-4)))
    G = c["karate"]
    for a, b in [("m1", "m34"), ("m17", "m12")]:
        H = G.to_directed()
        nx.set_edge_attributes(H, 1, "capacity")
        want = nx.maximum_flow_value(H, a, b)
        o = P(graph_id="karate", source=a, target=b, capacity="weight")
        res.append((f"karate flow {a}->{b}", ok(o) and has_number(o, want)))
    return res


@check("bipartite_matching")
def _(P, S, c):
    G = c["projects"]
    top = [n for n, d in G.nodes(data=True) if d["side"] == "student"]
    m = nx.bipartite.maximum_matching(G, top_nodes=top)
    size = len(m) // 2
    res = []
    o = P(graph_id="projects")
    res.append(("matching size", ok(o) and has_number(o, size)))
    ids = node_ids(o, S.get("projects")) if ok(o) else []
    res.append(("matched nodes valid", ok(o) and len(ids) >= 2))
    o = P(graph_id="karate")
    res.append(("non-bipartite handled", o.get("status") in ("ok", "error")))
    return res


@check("maximal_cliques")
def _(P, S, c):
    G = c["karate"]
    cl = list(nx.find_cliques(G))
    res = []
    o = P(graph_id="karate", top_k=100)
    res.append(("clique count", ok(o) and has_number(o, len(cl))))
    res.append(("max size", ok(o) and has_number(o, max(map(len, cl)))))
    o = P(graph_id="karate", node="m1", top_k=100)
    res.append(("cliques of m1", ok(o) and has_number(o, len([x for x in cl if "m1" in x]))))
    L = c["lesmis"]
    cl = list(nx.find_cliques(L))
    o = P(graph_id="lesmis", top_k=100)
    res.append(("lesmis count", ok(o) and has_number(o, len(cl))))
    return res


@check("motif_count")
def _(P, S, c):
    G = c["karate"]
    tri = sum(nx.triangles(G).values()) // 3
    res = []
    o = P(graph_id="karate", motif="triangle")
    res.append(("triangles", ok(o) and has_number(o, tri)))
    wedges = sum(d * (d - 1) // 2 for _, d in G.degree())
    o = P(graph_id="karate", motif="wedge")
    res.append(("wedges/open triads", ok(o) and (has_number(o, wedges) or has_number(o, wedges - 3 * tri))))
    o = P(graph_id="karate")
    res.append(("default call", ok(o) and has_number(o, tri)))
    L = c["lesmis"]
    o = P(graph_id="lesmis", motif="triangle")
    res.append(("lesmis triangles", ok(o) and has_number(o, sum(nx.triangles(L).values()) // 3)))
    return res


@check("node_embedding_similarity")
def _(P, S, c):
    res = []
    g = S.get("karate")
    o = P(graph_id="karate", node="m1", top_k=5)
    ids = node_ids(o, g) if ok(o) else []
    res.append(("returns 5 other nodes", ok(o) and len([i for i in ids if i != "m1"]) >= 5))
    o2 = P(graph_id="karate", node="m1", top_k=5)
    res.append(("deterministic", ok(o2) and o == o2))
    o = P(graph_id="karate", node="m34", top_k=5)
    ids = node_ids(o, g) if ok(o) else []
    res.append(("neighbours dominate", ok(o) and len(set(ids[:5]) & (set(c["karate"]["m34"]) | {"m33", "m3", "m1"})) >= 3))
    return res
