"""Check that an answer is supported by the tool outputs in the trace."""
from __future__ import annotations

import math
import re
from typing import Any


def _walk(obj):
    yield obj
    if isinstance(obj, dict):
        for v in obj.values():
            yield from _walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk(v)


class Evidence:
    """Everything the tools have told us so far."""

    def __init__(self):
        self.ids: set[str] = set()
        self.labels: dict[str, set[str]] = {}   # lower-case label -> node ids
        self.numbers: list[float] = []
        self.lengths: set[int] = set()          # lengths of lists the tools returned
        self.texts: list[str] = []
        self.calls = 0

    def add(self, output: dict) -> None:
        if not isinstance(output, dict) or output.get("status") != "ok":
            return
        self.calls += 1
        for x in _walk(output.get("result")):
            if isinstance(x, list):
                self.lengths.add(len(x))
                self.ids.update(v for v in x if isinstance(v, str) and len(v) < 40)  # e.g. a path as a list of ids
            if isinstance(x, dict) and isinstance(x.get("id"), str):
                self.ids.add(x["id"])
                if isinstance(x.get("label"), str):
                    self.labels.setdefault(x["label"].lower(), set()).add(x["id"])
            elif isinstance(x, (int, float)) and not isinstance(x, bool):
                self.numbers.append(float(x))
        summary = output.get("summary") or ""
        self.texts.append(summary)
        self.numbers += [float(m) for m in re.findall(r"-?\d+(?:\.\d+)?", summary)]

    def has_number(self, value: float, rel: float = 1e-3) -> bool:
        return any(math.isclose(v, value, rel_tol=rel, abs_tol=1e-6) for v in self.numbers)

    def derivable(self, value: float, rel: float = 1e-3) -> bool:
        """True if `value` is a list length, or a difference, sum or ratio of two tool numbers."""
        if value == int(value) and int(value) in self.lengths:
            return True
        nums = sorted(set(self.numbers))[:300]
        close = lambda a: math.isclose(a, value, rel_tol=rel, abs_tol=1e-6)  # noqa: E731
        for i, a in enumerate(nums):
            for b in nums[i:]:
                if close(b - a) or close(a + b) or (a and close(b / a)) or (b and close(a / b)):
                    return True
        return False

    def resolve_node(self, value: Any) -> str | None:
        """Map a model-supplied node (id, or label of a node we saw) to an id seen in tool output."""
        if not isinstance(value, str):
            return None
        if value in self.ids:
            return value
        ids = self.labels.get(value.strip().lower())
        if ids and len(ids) == 1:
            return next(iter(ids))
        return None


def check_answer(answer_type: str, value: Any, ev: Evidence) -> tuple[Any, str | None]:
    """Return (normalised value, problem). `problem` is None when the answer is supported."""
    if ev.calls == 0:
        return value, "No tool has returned a result yet, so nothing supports this answer."
    if answer_type == "node":
        nid = ev.resolve_node(value)
        return (nid or value), (None if nid else f"Node {value!r} never appears in any tool output.")
    if answer_type in ("node_list", "path"):
        if not isinstance(value, list):
            return value, f"{answer_type} must be a JSON array of node ids."
        out, bad = [], []
        for v in value:
            nid = ev.resolve_node(v)
            out.append(nid or v)
            if nid is None:
                bad.append(v)
        return out, (f"These nodes never appear in any tool output: {bad[:5]}." if bad else None)
    if answer_type == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return value, "number answers must be a JSON number."
        return value, None if ev.has_number(float(value)) or ev.derivable(float(value)) else \
            f"The number {value} does not appear in any tool output. If you derived it, " \
            "use only values the tools returned; otherwise call a tool that returns it."
    return value, None
