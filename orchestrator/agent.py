"""The agent loop: LLM plans -> tools run -> results flow back -> structured final answer."""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any

from graphkit.contract import error
from graphkit.llm import model_name, tool_schema
from graphkit.store import GraphStore
from graphkit.trace import Trace

from . import prompts
from .grounding import Evidence, check_answer
from .registry import ToolRegistry

MAX_TOOL_CALLS = 8      # hard cap per question; the prompt asks for at most 5 in normal cases
MAX_LLM_CALLS = 12
LLM_RETRIES = 4
ANSWER_TYPES = ("number", "boolean", "node", "node_list", "path", "text")
STATUSES = ("answered", "clarification_needed", "unsupported")


@dataclass
class Result:
    status: str
    answer_text: str
    answer: dict
    tools_used: list[str] = field(default_factory=list)


def _to_message(message: Any) -> dict:
    """Assistant message as a plain dict for the next request (keeps Gemini's thought signature)."""
    calls = []
    for c in message.tool_calls or []:
        entry = {"id": c.id, "type": "function",
                 "function": {"name": c.function.name, "arguments": c.function.arguments}}
        extra = getattr(c, "model_extra", None) or {}
        if "extra_content" in extra:
            entry["extra_content"] = extra["extra_content"]
        calls.append(entry)
    msg = {"role": "assistant", "content": message.content}
    if calls:
        msg["tool_calls"] = calls
    return msg


def parse_value(raw: Any, answer_type: str) -> Any:
    """Decode answer_value (JSON text, tolerating plain text) into a Python value."""
    if not isinstance(raw, str):
        return raw
    text = raw.strip()
    try:
        value = json.loads(text)
    except ValueError:
        if answer_type in ("node_list", "path") and text:
            return [t.strip().strip("\"'") for t in re.split(r"[,\n]|->", text.strip("[]")) if t.strip()]
        if answer_type == "number":
            m = re.search(r"-?\d+(?:\.\d+)?(?:[eE]-?\d+)?", text)
            return float(m.group()) if m else text
        if answer_type == "boolean":
            return text.lower() in ("true", "yes")
        return text
    if answer_type in ("node_list", "path") and isinstance(value, str):
        return [value]
    if answer_type == "node" and isinstance(value, list) and len(value) == 1:
        return value[0]
    if answer_type == "number" and isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            pass
    if answer_type == "boolean" and isinstance(value, str):
        return value.strip().lower() in ("true", "yes")
    return value


class Orchestrator:
    def __init__(self, client, registry: ToolRegistry, store: GraphStore, model: str | None = None):
        self.client, self.registry, self.store = client, registry, store
        self.model = model or model_name()
        self.schemas = [tool_schema(t.manifest) for t in registry] + [prompts.FINAL_ANSWER_SCHEMA]

    # ----- prompt -----
    def system_prompt(self) -> str:
        graphs = "\n".join(
            f"- {g['graph_id']}: {g['description']} ({g['nodes']} nodes, {g['edges']} edges, "
            f"{'directed' if g['directed'] else 'undirected'}, {'weighted' if g['weighted'] else 'unweighted'})"
            for g in self.store.list_graphs() if g["parent_id"] is None)
        return prompts.SYSTEM.format(max_tool_calls=MAX_TOOL_CALLS, graphs=graphs,
                                     tool_names=", ".join(self.registry.tools))

    # ----- LLM call with retry -----
    def _chat(self, messages: list, trace: Trace):
        last = None
        for attempt in range(LLM_RETRIES):
            try:
                resp = self.client.chat.completions.create(
                    model=self.model, messages=messages, tools=self.schemas, temperature=0)
                msg = resp.choices[0].message
                trace.llm_call(self.model, msg)
                return msg
            except Exception as exc:  # rate limits, timeouts, transient 5xx
                last = exc
                trace.error(f"LLM call failed (attempt {attempt + 1}): {type(exc).__name__}: {exc}")
                time.sleep(min(2 ** attempt * 2, 20))
        raise RuntimeError(f"LLM unavailable after {LLM_RETRIES} attempts: {last}")

    # ----- tool execution -----
    def run_tool(self, name: str, raw_args: str | None, cache: dict, trace: Trace) -> dict:
        try:
            args = json.loads(raw_args or "{}")
            if not isinstance(args, dict):
                raise ValueError("arguments must be a JSON object")
        except ValueError as exc:
            out = error(f"Arguments for '{name}' were not a valid JSON object ({exc}). Call it again with valid JSON.")
            trace.tool_call(name, {"_raw": raw_args}, out)
            return out
        tool = self.registry.get(name)
        if tool is None:
            out = error(f"Unknown tool '{name}'. Available tools: {', '.join(self.registry.tools)}.")
        elif "graph_id" not in args and "graph_id" in tool.manifest["parameters"].get("required", []):
            out = error("Missing required parameter 'graph_id'. Pass a dataset id or a result_graph_id from an earlier call.")
        else:
            key = (name, json.dumps(args, sort_keys=True))
            if key in cache:
                out = cache[key]
            else:
                out = tool.call(self.store, **args)
                if out.get("status") == "ok":
                    cache[key] = out
        trace.tool_call(name, args, out)
        return out

    # ----- one question -----
    def answer(self, question: str, trace: Trace, graph_hint: str | None = None) -> Result:
        trace.question(question)
        user = question if not graph_hint else f"{question}\n\n(The question concerns the graph '{graph_hint}'.)"
        messages = [{"role": "system", "content": self.system_prompt()}, {"role": "user", "content": user}]
        evidence, used, cache = Evidence(), [], {}
        n_calls, retried_grounding, nudged = 0, False, False

        for step in range(MAX_LLM_CALLS):
            try:
                msg = self._chat(messages, trace)
            except Exception as exc:
                return self._finish(trace, Result("error", f"ERROR: {exc}", {"type": "text", "value": None}, used))
            calls = msg.tool_calls or []
            if not calls:
                if nudged:
                    text = msg.content or ""
                    return self._finish(trace, Result("error", text or "The model did not call final_answer.",
                                                      {"type": "text", "value": text or None}, used))
                nudged = True
                messages.append(_to_message(msg))
                messages.append({"role": "user", "content": "Submit your answer by calling the final_answer tool."})
                continue

            messages.append(_to_message(msg))
            final = None
            for call in calls:
                name = call.function.name
                if name == "final_answer":
                    final = call
                    continue
                if n_calls >= MAX_TOOL_CALLS:
                    out = error(f"Tool-call budget of {MAX_TOOL_CALLS} is used up. Call final_answer now with what you have, "
                                "or with status unsupported if it is not enough.")
                    trace.tool_call(name, {}, out)
                else:
                    n_calls += 1
                    out = self.run_tool(name, call.function.arguments, cache, trace)
                    if out.get("status") == "ok" and self.registry.get(name):
                        impl = self.registry.implementation_id(name)
                        if impl not in used:
                            used.append(impl)
                    evidence.add(out)
                messages.append({"role": "tool", "tool_call_id": call.id,
                                 "content": json.dumps(out, ensure_ascii=False)})
            if final is not None:
                verdict = self._handle_final(final, evidence, used, retried_grounding, trace)
                if isinstance(verdict, Result):
                    return self._finish(trace, verdict)
                retried_grounding = True
                messages.append({"role": "tool", "tool_call_id": final.id, "content": verdict})
        return self._finish(trace, Result("error", "Ran out of LLM steps without a final answer.",
                                          {"type": "text", "value": None}, used))

    def _handle_final(self, call, evidence: Evidence, used: list, retried: bool, trace: Trace):
        """A Result if accepted, else a feedback string for the model."""
        try:
            a = json.loads(call.function.arguments or "{}")
        except ValueError:
            return "final_answer arguments were not valid JSON. Call final_answer again with valid JSON."
        status = a.get("status")
        atype = a.get("answer_type", "text")
        text = str(a.get("answer_text") or "")
        if status not in STATUSES:
            return f"status must be one of {STATUSES}. Call final_answer again."
        if atype not in ANSWER_TYPES:
            return f"answer_type must be one of {ANSWER_TYPES}. Call final_answer again."
        if status != "answered":
            return Result(status, text, {"type": "text", "value": text or None}, used)
        value = parse_value(a.get("answer_value"), atype)
        value, problem = check_answer(atype, value, evidence)
        if problem and not retried:
            trace.event("grounding_check", problem=problem)
            return (f"Your answer is not supported by the tool results: {problem} "
                    "Re-check the tool outputs, call a tool if needed, then call final_answer again. "
                    "If no tool can support an answer, use status unsupported.")
        if problem:
            trace.event("grounding_check", problem=problem, accepted_anyway=True)
        return Result("answered", text, {"type": atype, "value": value}, used)

    def _finish(self, trace: Trace, r: Result) -> Result:
        trace.event("final_answer", text=r.answer_text, status=r.status, answer=r.answer, tools_used=r.tools_used)
        return r
