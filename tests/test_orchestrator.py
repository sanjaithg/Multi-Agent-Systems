"""Offline tests: a scripted fake LLM drives the real agent loop and real tools."""
import json
from types import SimpleNamespace as NS

from graphkit import GraphStore
from graphkit.trace import Trace, read_trace
from orchestrator.agent import Orchestrator, parse_value
from orchestrator.grounding import Evidence, check_answer
from orchestrator.queries import load_queries
from orchestrator.registry import ToolRegistry


def call(name, **args):
    return NS(id=f"c_{name}", type="function", model_extra={},
              function=NS(name=name, arguments=json.dumps(args)))


class FakeClient:
    """Replays one scripted assistant message per request."""

    def __init__(self, script):
        self.script = list(script)
        self.requests = []
        self.chat = NS(completions=NS(create=self._create))

    def _create(self, **kw):
        self.requests.append(kw["messages"])
        msg = self.script.pop(0)
        return NS(choices=[NS(message=msg)])


def msg(*calls, content=None):
    return NS(role="assistant", content=content, tool_calls=list(calls),
              model_dump=lambda exclude_none=True: {"role": "assistant", "tool_calls": [c.function.name for c in calls]})


def final(**kw):
    return call("final_answer", **kw)


def run(script, tmp_path, question="q"):
    registry = ToolRegistry()
    agent = Orchestrator(FakeClient(script), registry, GraphStore(), model="fake")
    trace = Trace(tmp_path / "t.jsonl")
    return agent.answer(question, trace), read_trace(tmp_path / "t.jsonl")


def test_registry_discovers_tools_from_manifests():
    reg = ToolRegistry()
    assert {"lookup_node", "pagerank", "louvain"} <= set(reg.tools)
    assert all(t.manifest["implementation_id"].startswith(t.name + ".") or t.name in
               ("list_graphs", "lookup_node", "node_attributes", "filter_nodes") for t in reg)


def test_single_tool_answer_is_grounded_and_traced(tmp_path):
    script = [msg(call("pagerank", graph_id="karate", top_k=3)),
              msg(final(status="answered", answer_type="node", answer_value='"m34"', answer_text="Member 34."))]
    r, trace = run(script, tmp_path)
    assert r.status == "answered" and r.answer == {"type": "node", "value": "m34"}
    assert r.tools_used and r.tools_used[0].startswith("pagerank.")
    kinds = [e["type"] for e in trace]
    assert kinds[0] == "question" and kinds.count("llm_call") == 2 and "tool_call" in kinds and kinds[-1] == "final_answer"


def test_chaining_through_result_graph_id(tmp_path):
    reg = ToolRegistry()
    store = GraphStore()
    louv = reg["louvain"].call(store, graph_id="karate", top_k=1)
    gid = louv["result_graph_id"] or louv["result"][0]["graph_id"]
    script = [msg(call("louvain", graph_id="karate", top_k=5)),
              msg(call("pagerank", graph_id=gid, top_k=1)),
              msg(final(status="answered", answer_type="text", answer_value='"ok"', answer_text="chained"))]
    agent = Orchestrator(FakeClient(script), reg, store, model="fake")
    r = agent.answer("q", Trace(tmp_path / "t.jsonl"))
    assert r.status == "answered" and len(r.tools_used) == 2


def test_ungrounded_node_is_pushed_back_then_unsupported(tmp_path):
    script = [msg(call("pagerank", graph_id="karate", top_k=3)),
              msg(final(status="answered", answer_type="node", answer_value='"ZZZ"', answer_text="x")),
              msg(final(status="unsupported", answer_type="text", answer_value="null", answer_text="cannot"))]
    r, trace = run(script, tmp_path)
    assert r.status == "unsupported"
    assert any(e["type"] == "grounding_check" for e in trace)


def test_answer_without_any_tool_result_is_rejected(tmp_path):
    script = [msg(final(status="answered", answer_type="number", answer_value="5", answer_text="x")),
              msg(final(status="clarification_needed", answer_type="text", answer_value="null", answer_text="which graph?"))]
    r, _ = run(script, tmp_path)
    assert r.status == "clarification_needed"


def test_label_is_resolved_to_node_id():
    ev = Evidence()
    ev.add({"status": "ok", "result": [{"id": "MAA", "label": "Chennai International Airport", "score": 1}],
            "summary": "s", "result_graph_id": None, "error": None})
    assert check_answer("node", "Chennai International Airport", ev)[0] == "MAA"


def test_derived_numbers_are_accepted():
    ev = Evidence()
    ev.add({"status": "ok", "result": {"in_degree": 100}, "summary": "a has 100, b has 90", "result_graph_id": None, "error": None})
    assert check_answer("number", 10, ev)[1] is None      # 100 - 90
    assert check_answer("number", 12345, ev)[1] is not None


def test_bad_tool_arguments_do_not_crash(tmp_path):
    script = [msg(call("pagerank", graph_id="nope")),
              msg(final(status="unsupported", answer_type="text", answer_value="null", answer_text="no"))]
    r, trace = run(script, tmp_path)
    errs = [e for e in trace if e["type"] == "tool_call"]
    assert errs[0]["output"]["status"] == "error" and r.status == "unsupported"


def test_llm_failure_gives_error_status(tmp_path, monkeypatch):
    import orchestrator.agent as ag
    monkeypatch.setattr(ag.time, "sleep", lambda s: None)

    class Boom:
        chat = NS(completions=NS(create=lambda **kw: (_ for _ in ()).throw(RuntimeError("rate limit"))))
    agent = Orchestrator(Boom(), ToolRegistry(), GraphStore(), model="fake")
    r = agent.answer("q", Trace(tmp_path / "t.jsonl"))
    assert r.status == "error"


def test_parse_value_variants():
    assert parse_value("42", "number") == 42
    assert parse_value('["a","b"]', "node_list") == ["a", "b"]
    assert parse_value("a, b", "node_list") == ["a", "b"]
    assert parse_value("true", "boolean") is True
    assert parse_value('"m1"', "node") == "m1"


def test_query_loader_formats(tmp_path):
    (tmp_path / "a.json").write_text(json.dumps([{"query_id": "q1", "question": "A?"}, {"id": "x", "query": "B?", "graph": "karate"}]))
    (tmp_path / "b.txt").write_text("# c\nOne?\nTwo?\n")
    (tmp_path / "c.jsonl").write_text('{"question": "J1?"}\n{"question": "J2?"}\n')
    assert [q["query_id"] for q in load_queries(tmp_path / "a.json")] == ["q1", "x"]
    assert load_queries(tmp_path / "a.json")[1]["graph_id"] == "karate"
    assert [q["question"] for q in load_queries(tmp_path / "b.txt")] == ["One?", "Two?"]
    assert len(load_queries(tmp_path / "c.jsonl")) == 2
