# Graph Analytics Orchestrator

An LLM agent that answers natural-language questions about graphs by planning, calling and chaining tools
from the class registry (Assignment 3). Plain Python agent loop; no agent framework.

## Setup (Python 3.10+)

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export LLM_API_KEY=<your key>        # the environment variable name is LLM_API_KEY
```

`LLM_API_KEY` is the only required variable. Optional: `LLM_BASE_URL` and `LLM_MODEL`
(defaults: Gemini's OpenAI-compatible endpoint, `gemini-3.8-flash`; any OpenAI-compatible provider that supports
tool calling works, see `.env.example`). A `.env` file in the repo root is also read if present.

## Run (one command)

```bash
python run_queries.py --queries <file> --out answers.json
```

* `<file>` is JSON (a list of `{"query_id": ..., "question": ...}`; `id`/`query`/`text` are accepted aliases,
  and an optional `graph_id`), JSONL, or a plain text file with one question per line.
* `answers.json` gets one entry per question (`query_id`, `status`, `answer_text`, `answer{type,value}`,
  `tools_used`, `trace_file`). It is rewritten after every question, so a crash never loses finished answers.
* A trace per question is written to `traces/<query_id>.jsonl`: the question, every LLM call, every tool call with
  arguments and full output, any grounding check, and the final answer.
* Optional flags: `--traces DIR`, `--only q01,q07`.

Try it: `python run_queries.py --queries queries/sample_queries.json --out answers.json`, then
`python evaluate.py --answers answers.json --expected queries/sample_expected.json`.

## How it works

| Piece | File |
| --- | --- |
| Tool discovery: scans `infra_tools/` and `registry/tools/` for `tool.json` manifests at startup; nothing is hard-coded | `orchestrator/registry.py` |
| Agent loop: LLM call, tool execution, result chaining via `result_graph_id`, retries, tool-call budget, tracing | `orchestrator/agent.py` |
| Prompts and the structured `final_answer` schema | `orchestrator/prompts.py` |
| Grounding: an answer's nodes/numbers must appear in tool outputs of the same trace (or be a simple derivation of them) | `orchestrator/grounding.py` |
| Query-file reader | `orchestrator/queries.py` |
| CLI | `run_queries.py` |

The model sees every manifest as a function and one extra `final_answer` function whose arguments are the
structured answer (`status`, `answer_type`, `answer_value`, `answer_text`). Questions that are ambiguous or that no
tool supports end with status `clarification_needed` / `unsupported` instead of a guess. A `final_answer` with a node or
number that no tool output contains is pushed back once; if it still is not supported it is recorded
(`grounding_check` in the trace). LLM failures are retried with backoff; a question that still fails gets status `error`.
Each question gets a fresh graph store so subgraph ids never leak between questions.

## The registry: which implementations we kept

`registry/tools/` holds exactly one implementation per tool (33 tools). They were chosen by `curation/curate.py`,
which validated all 186 submitted implementations against the tool contract and ran per-tool checks against NetworkX
references (`curation/checks.py`: correctness on several graphs, determinism, graceful errors, runtime on `airports`).
Results for every candidate are in `curation/REPORT.md`. The losing candidates are not shipped; to re-run curation, put
the full registry in `curation/candidates/<tool>/<id>/` and run `python curation/curate.py --apply`.

## Layout

```
run_queries.py  evaluate.py  requirements.txt  .env.example
orchestrator/   agent, registry, prompts, grounding, queries
graphkit/       shared library from Assignment 3 (store, contract, validator, trace, llm)
data/           datasets          infra_tools/  list_graphs, lookup_node, node_attributes, filter_nodes
registry/tools/ the chosen implementations (one per tool)
curation/       selection scripts and report         queries/  sample questions + reference answers
tests/          pytest (offline: a scripted fake LLM drives the real loop and tools)
report/         project report source
```

Tests: `python -m pytest -q` (no API key needed).
