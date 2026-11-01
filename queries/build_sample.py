"""Build queries/sample_queries.json and queries/sample_expected.json (reference answers from NetworkX).

This is our own stand-in for the instructors' public set; it only checks plumbing and behaviour.
Run from the repo root:  python queries/build_sample.py
"""
import json
import sys
from pathlib import Path

import networkx as nx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from graphkit import GraphStore  # noqa: E402
from graphkit.testing import to_networkx  # noqa: E402

store = GraphStore()
K, L, A, C, P = (to_networkx(store.get(g)) for g in ("karate", "lesmis", "airports", "courses", "projects"))
Q, E = [], {}


def add(question, status, atype=None, value=None, ordered=False):
    qid = f"s{len(Q) + 1:02d}"
    Q.append({"query_id": qid, "question": question})
    E[qid] = {"status": status, "type": atype, "value": value, "ordered": ordered}


def top(d, k):
    return [n for n, _ in sorted(d.items(), key=lambda kv: (-kv[1], kv[0]))[:k]]


# ---- single tool
add("How many members are in the karate club network?", "answered", "number", 34)
add("How many friendships (edges) does the karate club network contain?", "answered", "number", 78)
add("Which airport has the most non-stop routes departing from it?", "answered", "node", top(dict(A.out_degree()), 1)[0])
add("Who are the 3 most influential members of the karate club according to PageRank?", "answered", "node_list", top(nx.pagerank(K, tol=1e-12), 3), True)
add("What is the diameter of the karate club network?", "answered", "number", nx.diameter(K))
add("Is the project-assignment network bipartite?", "answered", "boolean", True)
add("How many triangles are there in the karate club network?", "answered", "number", sum(nx.triangles(K).values()) // 3)
add("How many maximal cliques does the karate club network have?", "answered", "number", len(list(nx.find_cliques(K))))
add("What is the size of the largest possible matching between students and projects?", "answered", "number",
    len(nx.bipartite.maximum_matching(P, top_nodes=[n for n, d in P.nodes(data=True) if d["side"] == "student"])) // 2)
add("Which Les Miserables character has the highest betweenness centrality?", "answered", "node", top(nx.betweenness_centrality(L), 1)[0])
add("Which karate club members are articulation points (cut vertices)?", "answered", "node_list", sorted(nx.articulation_points(K)))
add("How many strongly connected components does the airline network have?", "answered", "number", nx.number_strongly_connected_components(A))
add("How many members are in the 3-core of the karate club network?", "answered", "number", len(nx.k_core(K, 3)))
add("Is it possible to reach course CS101 from course CS102 by following prerequisites forwards?", "answered", "boolean", nx.has_path(C, "CS102", "CS101"))
add("What is the minimum number of non-stop flights needed to get from Chennai to Anchorage?", "answered", "number", nx.shortest_path_length(A, "MAA", "ANC"))
add("What is the shortest flying distance in km from Delhi to Sydney using the available routes?", "answered", "number",
    nx.dijkstra_path_length(A, "DEL", "SYD", weight="weight"))
add("What is the average clustering coefficient of the karate club network?", "answered", "number", nx.average_clustering(K))
add("Which course has the highest in-degree, i.e. is a prerequisite-target of the most courses?", "answered", "node", top(dict(C.in_degree()), 1)[0])
# ---- multi-step
H = A.subgraph(nx.single_source_shortest_path_length(A, "MAA", cutoff=2))
add("Among the airports reachable from Chennai within 2 non-stop hops, which one has the highest PageRank within that sub-network?",
    "answered", "node", top(nx.pagerank(H, tol=1e-12), 1)[0])
ind = [n for n, d in A.nodes(data=True) if d["country"] == "India"]
add("Among the airports in India, which has the most non-stop routes to other Indian airports?", "answered", "node",
    top(dict(A.subgraph(ind).out_degree()), 1)[0])
add("What is the clustering coefficient of the karate club member with the highest betweenness centrality?", "answered", "number",
    nx.clustering(K, top(nx.betweenness_centrality(K), 1)[0]))
add("How many members are within 2 hops of the club's instructor in the karate network?", "answered", "number",
    len(nx.single_source_shortest_path_length(K, "m1", cutoff=2)) - 1)
add("What is the shortest path from the karate club administrator to the instructor?", "answered", "path",
    nx.shortest_path(K, "m34", "m1"))
add("How many airports are located in India?", "answered", "number", len(ind))
# ---- ambiguous
add("What is the shortest route from London to Paris?", "clarification_needed")
add("Which airport is the best?", "clarification_needed")
add("Who is the most important one?", "clarification_needed")
# ---- unsupported
add("What will be the cheapest ticket price from Chennai to Delhi next month?", "unsupported")
add("Which airport will have the most traffic in 2030?", "unsupported")
add("Add a new direct route from Chennai to Anchorage and recompute the network's PageRank.", "unsupported")
add("Why did the karate club split into two groups?", "unsupported")

(ROOT / "queries" / "sample_queries.json").write_text(json.dumps(Q, indent=2), encoding="utf-8")
(ROOT / "queries" / "sample_expected.json").write_text(json.dumps(E, indent=2), encoding="utf-8")
print(len(Q), "questions")
