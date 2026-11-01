"""Discover tools by reading manifests at startup; nothing is hard-coded."""
from __future__ import annotations

import re
import sys
from pathlib import Path

from graphkit.loader import Tool, load_manifest, load_tool

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ROOTS = (ROOT / "infra_tools", ROOT / "registry" / "tools")


class ToolRegistry:
    """name -> Tool, built by scanning folders that contain a tool.json."""

    def __init__(self, *roots: str | Path):
        self.tools: dict[str, Tool] = {}
        self.skipped: list[str] = []
        for root in roots or DEFAULT_ROOTS:
            for manifest_path in sorted(Path(root).rglob("tool.json")):
                if "template" in manifest_path.parts:
                    continue
                self._add(manifest_path.parent)

    def _add(self, folder: Path) -> None:
        try:
            manifest = load_manifest(folder)
            name = manifest["name"]
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", name):
                raise ValueError(f"tool name {name!r} is not a valid function name")
            if name in self.tools:
                raise ValueError(f"duplicate tool name {name!r} (keep one implementation per tool)")
            self.tools[name] = load_tool(folder)
        except Exception as exc:  # a broken tool must not stop the orchestrator
            self.skipped.append(f"{folder}: {exc}")
            print(f"[registry] skipped {folder}: {exc}", file=sys.stderr)

    def __getitem__(self, name: str) -> Tool:
        return self.tools[name]

    def get(self, name: str):
        return self.tools.get(name)

    def __iter__(self):
        return iter(self.tools.values())

    def __len__(self) -> int:
        return len(self.tools)

    def implementation_id(self, name: str) -> str:
        return self.tools[name].implementation_id
