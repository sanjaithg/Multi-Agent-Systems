# Tool curation report

Every candidate was validated against the tool contract and tested against NetworkX references (`curation/checks.py`). One implementation per tool was kept.

| tool | chosen | candidates | chosen score | failed checks of chosen | runner-up |
|---|---|---|---|---|---|
| articulation_points_bridges | 3237bc9e | 3 | 108.0 | - | 8f0a9ac4 (108.0) |
| betweenness_centrality | 2f7893e5 | 8 | 107.95 | - | fcd76f91 (107.93) |
| bipartite_check | 3c8c3c69 | 4 | 108.0 | - | 62a230f4 (108.0) |
| bipartite_matching | 3f28ff34 | 8 | 108.0 | - | 54d073a3 (108.0) |
| closeness_centrality | 7065a2b5 | 5 | 107.96 | - | 7b0e9b7e (82.98) |
| clustering_coefficient | 219c8a12 | 7 | 108.0 | - | d02c8330 (108.0) |
| connected_components | 3237bc9e | 7 | 108.0 | - | 4ebce3f0 (108.0) |
| degree_centrality | 54d073a3 | 5 | 108.0 | - | 62a230f4 (108.0) |
| degree_distribution | 63fb3e40 | 7 | 108.0 | - | 6e31812a (108.0) |
| diameter_eccentricity | ae9bcafc | 4 | 107.97 | - | ab9fb3a3 (107.97) |
| ego_network | b2d75536 | 6 | 108.0 | - | d35c782d (108.0) |
| girvan_newman | 3237bc9e | 8 | 106.0 | - | 3c8c3c69 (106.0) |
| graph_summary | 2f7893e5 | 6 | 108.0 | - | 41c8e8e2 (108.0) |
| greedy_coloring | 4ebce3f0 | 4 | 108.0 | - | f28f69d7 (108.0) |
| hits | 219c8a12 | 4 | 108.0 | - | 98eff80e (108.0) |
| k_core | 3f28ff34 | 4 | 108.0 | - | 51616f3b (108.0) |
| k_hop_neighborhood | 32016695 | 6 | 108.0 | - | 3c8c3c69 (108.0) |
| label_propagation | 39bca602 | 4 | 107.99 | - | 6ae0e02c (107.99) |
| link_prediction | 41c8e8e2 | 5 | 108.0 | - | 37c243f2 (107.98) |
| louvain | f3b11984 | 7 | 107.99 | - | e7c02e9e (107.98) |
| max_flow_min_cut | 1e59ba80 | 8 | 108.0 | - | 32016695 (108.0) |
| maximal_cliques | 6e31812a | 8 | 107.98 | - | 7065a2b5 (107.98) |
| minimum_spanning_tree | b2eb4e3d | 5 | 108.0 | - | 3ddaa37e (106.0) |
| motif_count | ae9bcafc | 8 | 107.99 | - | e1e14ad1 (107.99) |
| node_embedding_similarity | b2eb4e3d | 7 | 108.0 | - | 39bca602 (107.99) |
| node_similarity | 29a7a55d | 6 | 108.0 | - | 39bca602 (108.0) |
| pagerank | 29a7a55d | 3 | 108.0 | - | da50612d (108.0) |
| personalized_pagerank | e7c02e9e | 4 | 108.0 | - | e1e14ad1 (108.0) |
| reachability | 7780ae37 | 6 | 108.0 | - | 7cc0c2d7 (108.0) |
| shortest_path_unweighted | 8809b513 | 6 | 108.0 | - | 8f0a9ac4 (108.0) |
| shortest_path_weighted | 32016695 | 4 | 108.0 | - | 91f2b762 (108.0) |
| strongly_connected_components | 2f7893e5 | 4 | 108.0 | - | e2346c64 (108.0) |
| topological_sort | 63fb3e40 | 5 | 108.0 | - | 1e59ba80 (108.0) |

## All candidates

| tool | impl | score | correct | validate errors | failed checks |
|---|---|---|---|---|---|
| articulation_points_bridges | 3237bc9e | 108.0 | 1.0 |  | - |
| articulation_points_bridges | 8f0a9ac4 | 108.0 | 1.0 |  | - |
| articulation_points_bridges | f6f61ae0 | 106.0 | 1.0 |  | - |
| betweenness_centrality | 2f7893e5 | 107.95 | 1.0 |  | - |
| betweenness_centrality | fcd76f91 | 107.93 | 1.0 |  | - |
| betweenness_centrality | 98eff80e | 107.9 | 1.0 |  | - |
| betweenness_centrality | f6f61ae0 | 107.86 | 1.0 |  | - |
| betweenness_centrality | c1fb2ea9 | 87.85 | 0.8 |  | lesmis top5 (weighted flag) |
| betweenness_centrality | 7b0e9b7e | 67.95 | 0.6 |  | unnormalized, lesmis top5 (weighted flag) |
| betweenness_centrality | f897d4c5 | 67.85 | 0.6 |  | unnormalized, lesmis top5 (weighted flag) |
| betweenness_centrality | d69742a9 | 67.55 | 0.6 |  | unnormalized, lesmis top5 (unweighted) |
| bipartite_check | 3c8c3c69 | 108.0 | 1.0 |  | - |
| bipartite_check | 62a230f4 | 108.0 | 1.0 |  | - |
| bipartite_check | 6e31812a | 108.0 | 1.0 |  | - |
| bipartite_check | 7780ae37 | 108.0 | 1.0 |  | - |
| bipartite_matching | 3f28ff34 | 108.0 | 1.0 |  | - |
| bipartite_matching | 54d073a3 | 108.0 | 1.0 |  | - |
| bipartite_matching | 8809b513 | 108.0 | 1.0 |  | - |
| bipartite_matching | 8f0a9ac4 | 108.0 | 1.0 |  | - |
| bipartite_matching | c52598eb | 108.0 | 1.0 |  | - |
| bipartite_matching | d02c8330 | 108.0 | 1.0 |  | - |
| bipartite_matching | e2346c64 | 108.0 | 1.0 |  | - |
| bipartite_matching | f9857550 | 108.0 | 1.0 |  | - |
| closeness_centrality | 7065a2b5 | 107.96 | 1.0 |  | - |
| closeness_centrality | 7b0e9b7e | 82.98 | 0.75 |  | single node |
| closeness_centrality | 7cc0c2d7 | 82.97 | 0.75 |  | single node |
| closeness_centrality | 64036f4f | 82.96 | 0.75 |  | single node |
| closeness_centrality | afc500fb | 31.0 | 0.25 |  | karate top5, score value, airports top5 (in) |
| clustering_coefficient | 219c8a12 | 108.0 | 1.0 |  | - |
| clustering_coefficient | d02c8330 | 108.0 | 1.0 |  | - |
| clustering_coefficient | da50612d | 108.0 | 1.0 |  | - |
| clustering_coefficient | 6ae0e02c | 107.98 | 1.0 |  | - |
| clustering_coefficient | 7065a2b5 | 107.98 | 1.0 |  | - |
| clustering_coefficient | 7b0e9b7e | 107.98 | 1.0 |  | - |
| clustering_coefficient | 3ddaa37e | 106.0 | 1.0 |  | - |
| connected_components | 3237bc9e | 108.0 | 1.0 |  | - |
| connected_components | 4ebce3f0 | 108.0 | 1.0 |  | - |
| connected_components | e2346c64 | 108.0 | 1.0 |  | - |
| connected_components | f9857550 | 108.0 | 1.0 |  | - |
| connected_components | 991d1029 | 106.0 | 1.0 |  | - |
| connected_components | 1e59ba80 | 106.0 | 1.0 |  | - |
| connected_components | 37c243f2 | 106.0 | 1.0 |  | - |
| degree_centrality | 54d073a3 | 108.0 | 1.0 |  | - |
| degree_centrality | 62a230f4 | 108.0 | 1.0 |  | - |
| degree_centrality | c52598eb | 108.0 | 1.0 |  | - |
| degree_centrality | a018559c | 108.0 | 1.0 |  | - |
| degree_centrality | f897d4c5 | 108.0 | 1.0 |  | - |
| degree_distribution | 63fb3e40 | 108.0 | 1.0 |  | - |
| degree_distribution | 6e31812a | 108.0 | 1.0 |  | - |
| degree_distribution | c1fb2ea9 | 108.0 | 1.0 |  | - |
| degree_distribution | c4576e71 | 108.0 | 1.0 |  | - |
| degree_distribution | c7c2ef65 | 108.0 | 1.0 |  | - |
| degree_distribution | f3b11984 | 108.0 | 1.0 |  | - |
| degree_distribution | efd53284 | 74.67 | 0.6666666666666666 |  | mean degree |
| diameter_eccentricity | ae9bcafc | 107.97 | 1.0 |  | - |
| diameter_eccentricity | ab9fb3a3 | 107.97 | 1.0 |  | - |
| diameter_eccentricity | 991d1029 | 107.96 | 1.0 |  | - |
| diameter_eccentricity | d69742a9 | 57.76 | 0.5 |  | radius, lesmis diameter |
| ego_network | b2d75536 | 108.0 | 1.0 |  | - |
| ego_network | d35c782d | 108.0 | 1.0 |  | - |
| ego_network | 51616f3b | 108.0 | 1.0 |  | - |
| ego_network | e1e14ad1 | 108.0 | 1.0 |  | - |
| ego_network | 98eff80e | 83.0 | 0.75 |  | airports in ego |
| ego_network | afc500fb | 83.0 | 0.75 |  | airports in ego |
| girvan_newman | 3237bc9e | 106.0 | 1.0 |  | - |
| girvan_newman | 3c8c3c69 | 106.0 | 1.0 |  | - |
| girvan_newman | 80ae2fd8 | 106.0 | 1.0 |  | - |
| girvan_newman | c7c2ef65 | 106.0 | 1.0 |  | - |
| girvan_newman | 64036f4f | 106.0 | 1.0 |  | - |
| girvan_newman | afc500fb | 106.0 | 1.0 |  | - |
| girvan_newman | 219c8a12 | 103.16 | 1.0 |  | - |
| girvan_newman | d35c782d | 100.0 | 1.0 |  | - |
| graph_summary | 2f7893e5 | 108.0 | 1.0 |  | - |
| graph_summary | 41c8e8e2 | 108.0 | 1.0 |  | - |
| graph_summary | 5c98c8eb | 108.0 | 1.0 |  | - |
| graph_summary | 64036f4f | 108.0 | 1.0 |  | - |
| graph_summary | a20d8c29 | 108.0 | 1.0 |  | - |
| graph_summary | 80ae2fd8 | 88.0 | 0.8 |  | airports directed |
| greedy_coloring | 4ebce3f0 | 108.0 | 1.0 |  | - |
| greedy_coloring | f28f69d7 | 108.0 | 1.0 |  | - |
| greedy_coloring | 54d073a3 | 108.0 | 1.0 |  | - |
| greedy_coloring | 8809b513 | 108.0 | 1.0 |  | - |
| hits | 219c8a12 | 108.0 | 1.0 |  | - |
| hits | 98eff80e | 108.0 | 1.0 |  | - |
| hits | a20d8c29 | 108.0 | 1.0 |  | - |
| hits | f9857550 | 108.0 | 1.0 |  | - |
| k_core | 3f28ff34 | 108.0 | 1.0 |  | - |
| k_core | 51616f3b | 108.0 | 1.0 |  | - |
| k_core | b2d75536 | 108.0 | 1.0 |  | - |
| k_core | d02c8330 | 108.0 | 1.0 |  | - |
| k_hop_neighborhood | 32016695 | 108.0 | 1.0 |  | - |
| k_hop_neighborhood | 3c8c3c69 | 108.0 | 1.0 |  | - |
| k_hop_neighborhood | b2eb4e3d | 108.0 | 1.0 |  | - |
| k_hop_neighborhood | e7c02e9e | 108.0 | 1.0 |  | - |
| k_hop_neighborhood | 3f28ff34 | 83.0 | 0.75 |  | airports in 1-hop |
| k_hop_neighborhood | f1f54c61 | 83.0 | 0.75 |  | airports in 1-hop |
| label_propagation | 39bca602 | 107.99 | 1.0 |  | - |
| label_propagation | 6ae0e02c | 107.99 | 1.0 |  | - |
| label_propagation | a018559c | 107.99 | 1.0 |  | - |
| label_propagation | f1f54c61 | 82.99 | 0.75 |  | communities plausible |
| link_prediction | 41c8e8e2 | 108.0 | 1.0 |  | - |
| link_prediction | 37c243f2 | 107.98 | 1.0 |  | - |
| link_prediction | d35c782d | 107.98 | 1.0 |  | - |
| link_prediction | eaf1d77a | 107.98 | 1.0 |  | - |
| link_prediction | 92711a92 | 107.97 | 1.0 |  | - |
| louvain | f3b11984 | 107.99 | 1.0 |  | - |
| louvain | e7c02e9e | 107.98 | 1.0 |  | - |
| louvain | f28f69d7 | 107.98 | 1.0 |  | - |
| louvain | c4576e71 | 107.97 | 1.0 |  | - |
| louvain | f1f54c61 | 106.0 | 1.0 |  | - |
| louvain | 91f2b762 | 87.99 | 0.8 |  | deterministic |
| louvain | b2d75536 | 87.99 | 0.8 |  | deterministic |
| max_flow_min_cut | 1e59ba80 | 108.0 | 1.0 |  | - |
| max_flow_min_cut | 32016695 | 108.0 | 1.0 |  | - |
| max_flow_min_cut | 991d1029 | 108.0 | 1.0 |  | - |
| max_flow_min_cut | da50612d | 108.0 | 1.0 |  | - |
| max_flow_min_cut | 29a7a55d | 108.0 | 1.0 |  | - |
| max_flow_min_cut | 3ddaa37e | 108.0 | 1.0 |  | - |
| max_flow_min_cut | edba08e8 | 108.0 | 1.0 |  | - |
| max_flow_min_cut | 5c98c8eb | 58.0 | 0.5 |  | karate flow m1->m34, karate flow m17->m12 |
| maximal_cliques | 6e31812a | 107.98 | 1.0 |  | - |
| maximal_cliques | 7065a2b5 | 107.98 | 1.0 |  | - |
| maximal_cliques | 92711a92 | 107.98 | 1.0 |  | - |
| maximal_cliques | 6ae0e02c | 106.0 | 1.0 |  | - |
| maximal_cliques | a018559c | 82.98 | 0.75 |  | cliques of m1 |
| maximal_cliques | a20d8c29 | 82.97 | 0.75 |  | cliques of m1 |
| maximal_cliques | 62a230f4 | 81.0 | 0.75 |  | cliques of m1 |
| maximal_cliques | ab9fb3a3 | 6.0 | 0.0 |  | clique count, max size, cliques of m1, lesmis count |
| minimum_spanning_tree | b2eb4e3d | 108.0 | 1.0 |  | - |
| minimum_spanning_tree | 3ddaa37e | 106.0 | 1.0 |  | - |
| minimum_spanning_tree | 5c98c8eb | 106.0 | 1.0 |  | - |
| minimum_spanning_tree | 96e40bd2 | 106.0 | 1.0 |  | - |
| minimum_spanning_tree | edba08e8 | 106.0 | 1.0 |  | - |
| motif_count | ae9bcafc | 107.99 | 1.0 |  | - |
| motif_count | e1e14ad1 | 107.99 | 1.0 |  | - |
| motif_count | 51616f3b | 107.98 | 1.0 |  | - |
| motif_count | 63fb3e40 | 107.96 | 1.0 |  | - |
| motif_count | 81c01533 | 107.96 | 1.0 |  | - |
| motif_count | eaf1d77a | 107.95 | 1.0 |  | - |
| motif_count | 37c243f2 | 82.93 | 0.75 |  | wedges/open triads |
| motif_count | 7cc0c2d7 | 32.98 | 0.25 |  | triangles, wedges/open triads, default call |
| node_embedding_similarity | b2eb4e3d | 108.0 | 1.0 |  | - |
| node_embedding_similarity | 39bca602 | 107.99 | 1.0 |  | - |
| node_embedding_similarity | 96e40bd2 | 107.99 | 1.0 |  | - |
| node_embedding_similarity | 41c8e8e2 | 107.98 | 1.0 |  | - |
| node_embedding_similarity | 7780ae37 | 107.96 | 1.0 |  | - |
| node_embedding_similarity | efd53284 | 107.86 | 1.0 |  | - |
| node_embedding_similarity | 4ebce3f0 | 107.76 | 1.0 |  | - |
| node_similarity | 29a7a55d | 108.0 | 1.0 |  | - |
| node_similarity | 39bca602 | 108.0 | 1.0 |  | - |
| node_similarity | 81c01533 | 108.0 | 1.0 |  | - |
| node_similarity | ab9fb3a3 | 108.0 | 1.0 |  | - |
| node_similarity | d69742a9 | 108.0 | 1.0 |  | - |
| node_similarity | eaf1d77a | 108.0 | 1.0 |  | - |
| pagerank | 29a7a55d | 108.0 | 1.0 |  | - |
| pagerank | da50612d | 108.0 | 1.0 |  | - |
| pagerank | f3b11984 | 108.0 | 1.0 |  | - |
| personalized_pagerank | e7c02e9e | 108.0 | 1.0 |  | - |
| personalized_pagerank | e1e14ad1 | 108.0 | 1.0 |  | - |
| personalized_pagerank | 81c01533 | 107.99 | 1.0 |  | - |
| personalized_pagerank | c52598eb | 107.99 | 1.0 |  | - |
| reachability | 7780ae37 | 108.0 | 1.0 |  | - |
| reachability | 7cc0c2d7 | 108.0 | 1.0 |  | - |
| reachability | 91f2b762 | 108.0 | 1.0 |  | - |
| reachability | 92711a92 | 108.0 | 1.0 |  | - |
| reachability | f6f61ae0 | 108.0 | 1.0 |  | - |
| reachability | fcd76f91 | 108.0 | 1.0 |  | - |
| shortest_path_unweighted | 8809b513 | 108.0 | 1.0 |  | - |
| shortest_path_unweighted | 8f0a9ac4 | 108.0 | 1.0 |  | - |
| shortest_path_unweighted | 96e40bd2 | 108.0 | 1.0 |  | - |
| shortest_path_unweighted | ae9bcafc | 108.0 | 1.0 |  | - |
| shortest_path_unweighted | edba08e8 | 108.0 | 1.0 |  | - |
| shortest_path_unweighted | f28f69d7 | 108.0 | 1.0 |  | - |
| shortest_path_weighted | 32016695 | 108.0 | 1.0 |  | - |
| shortest_path_weighted | 91f2b762 | 108.0 | 1.0 |  | - |
| shortest_path_weighted | c4576e71 | 108.0 | 1.0 |  | - |
| shortest_path_weighted | f897d4c5 | 108.0 | 1.0 |  | - |
| strongly_connected_components | 2f7893e5 | 108.0 | 1.0 |  | - |
| strongly_connected_components | e2346c64 | 108.0 | 1.0 |  | - |
| strongly_connected_components | fcd76f91 | 108.0 | 1.0 |  | - |
| strongly_connected_components | 80ae2fd8 | 83.0 | 0.75 |  | largest subgraph |
| topological_sort | 63fb3e40 | 108.0 | 1.0 |  | - |
| topological_sort | 1e59ba80 | 108.0 | 1.0 |  | - |
| topological_sort | c1fb2ea9 | 108.0 | 1.0 |  | - |
| topological_sort | c7c2ef65 | 108.0 | 1.0 |  | - |
| topological_sort | efd53284 | 108.0 | 1.0 |  | - |
