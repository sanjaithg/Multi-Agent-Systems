# Graph Analytics Orchestrator: Project Report

Group: <group name / members>  ·  Model used: <e.g. gemini-3.8-flash>

## 1. Design

**Agent loop.** A plain-Python loop (`orchestrator/agent.py`) gives the LLM every tool as a function, plus one extra
function, `final_answer`, whose arguments *are* the structured answer (`status`, `answer_type`, `answer_value`,
`answer_text`). The model plans implicitly: it calls tools (several per turn are allowed), reads each result's
`summary`/`result`, and finishes by calling `final_answer`. The cap is 8 tool calls and 12 LLM calls per question; the
prompt asks for at most five and says to stop early.

**Discovery and curation.** At startup `ToolRegistry` scans the manifests under `infra_tools/` and `registry/tools/`
and builds the function list from `tool.json`; adding or removing a tool folder changes the agent with no code change.
Of 186 submitted implementations we kept one per tool. `curation/curate.py` validates each against the contract, then
compares it with NetworkX on karate, lesmis, courses, projects and airports (rankings, partitions, subgraph node sets,
path validity and cost, flow values, ...), and also scores determinism, graceful errors and airports runtime. Every
chosen implementation passes all of our checks; the per-candidate table is `curation/REPORT.md`. <Add: notable findings,
e.g. how many candidates failed which checks.>

**Chaining.** Tools that create subgraphs return `result_graph_id` (and a `graph_id` per community/component); the
prompt tells the model to pass these as `graph_id` to the next call ("most influential member of the largest community"
= louvain, then pagerank on that community's id). Node names go through `lookup_node` first.

**Grounding.** The structured answer is checked against an `Evidence` object built from the tool outputs in the same
trace: a node must appear in some output (labels are mapped back to ids), a number must appear in an output or be a list
length / sum / difference / ratio of output numbers, and an answer with no tool result at all is refused. A failing
answer is returned to the model once with the reason; if it still fails it is kept but logged. `evaluate.py` applies the
same test, mirroring the "unsupported by the trace counts as wrong" rule.

**Ambiguous and unsupported questions.** The prompt defines both cases (several materially different readings and no
sensible default; or information/operations beyond the graphs and tools) and tells the model to prefer a standard reading
when one exists (e.g. "most influential" = PageRank) and state the assumption. Statuses are returned as
`clarification_needed` / `unsupported`.

**Robustness.** Tool crashes become contract errors; bad JSON arguments and unknown tools are reported back to the model;
identical successful calls are cached; LLM errors are retried with backoff and end as status `error`; the answers file
is written after each question; each question gets a fresh store.

**Traces.** `traces/<query_id>.jsonl`: question, every LLM call, every tool call (arguments + full output), grounding
checks, final answer with status and tools used.

## 2. Results on the public set

<Fill in after running: `python run_queries.py --queries <public file> --out answers_public.json` and `python evaluate.py`.>

| Category | Questions | Correct |
| --- | --- | --- |
| Single-tool | | |
| Multi-step | | |
| Ambiguous | | |
| Unsupported | | |
| **Total** | | |

Mean / max tool calls per question: <..>. Model, temperature (0), runtime: <..>.

## 3. Failure analysis

<At least three failures, each: question, what the trace shows, root cause (prompt / tool / data / grading), fix or limitation.>

1. 
2. 
3. 

## 4. Member contributions

| Member | Role | Contribution |
| --- | --- | --- |
| | Planner | |
| | Executor | |
| | Tool curator | |
| | Evaluation lead | |
| | Integration / demo | |
