"""Native AST compact projection for Python semantic query items."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from python_lang_project_harness._python_outline import (
    fallback_python_compact,
    render_python_outline,
)
from python_lang_project_harness._python_projection import (
    CompactPythonProjectionNode,
    collect_python_projection_node,
)
from python_lang_project_harness._python_source import parse_python_lines


@dataclass(frozen=True)
class CompactPythonItem:
    """Compact code and parser-owned projection nodes for one Python item."""

    code: str
    projection_nodes: list[dict[str, Any]]


def compact_python_item(
    raw_lines: list[str],
    owner_path: str,
    start_line: int,
) -> CompactPythonItem:
    """Return AST-owned compact code and projection nodes for source lines."""

    tree = parse_python_lines(raw_lines)
    if tree is None:
        return CompactPythonItem(
            code=fallback_python_compact(raw_lines),
            projection_nodes=[],
        )
    projection_nodes: list[CompactPythonProjectionNode] = []
    for node in tree.body:
        collect_python_projection_node(
            projection_nodes,
            node,
            owner_path=owner_path,
            start_line=start_line,
            depth=0,
        )
    return CompactPythonItem(
        code=render_python_outline(tree),
        projection_nodes=[node.as_packet_node() for node in projection_nodes[:80]],
    )
