"""AST fallback windows for Python direct-source-read selectors."""

from __future__ import annotations

import ast
from typing import Any

from ._python_compact import compact_python_item


def ast_selector_range_items(
    source_lines: list[str],
    owner_path: str,
    selector_range: tuple[int, int],
) -> list[dict[str, Any]]:
    """Return top-level function/class items overlapping a selector range."""

    source_text = "\n".join(source_lines)
    try:
        module = ast.parse(source_text)
    except SyntaxError:
        return []
    start_line, end_line = selector_range
    items = [
        _ast_item_record(source_lines, owner_path, node)
        for node in module.body
        if isinstance(node, (ast.AsyncFunctionDef, ast.ClassDef, ast.FunctionDef))
        and _ast_node_overlaps_range(node, start_line, end_line)
    ]
    return [item for item in items if item is not None]


def prefer_ast_range_items(
    parser_items: list[dict[str, Any]],
    ast_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Prefer AST source windows when they own the selected Python range."""

    if ast_items:
        return ast_items
    return parser_items


def _ast_item_record(
    source_lines: list[str],
    owner_path: str,
    node: ast.AsyncFunctionDef | ast.ClassDef | ast.FunctionDef,
) -> dict[str, Any] | None:
    end_line = getattr(node, "end_lineno", None)
    if not isinstance(end_line, int):
        return None
    start_line = node.lineno
    raw_lines = source_lines[start_line - 1 : end_line]
    compact = compact_python_item(raw_lines, owner_path, start_line)
    code = compact.code if compact.projection_nodes else "\n".join(raw_lines).rstrip()
    return {
        "name": node.name,
        "kind": "class" if isinstance(node, ast.ClassDef) else "function",
        "ownerPath": owner_path,
        "location": {
            "path": owner_path,
            "lineRange": f"{start_line}:{end_line}",
        },
        "fields": {
            "public": not node.name.startswith("_"),
            "read": f"{owner_path}:{start_line}:{end_line}",
            "reason": "ast-range-fallback",
            "truncated": False,
            "code": code,
            "projectionNodes": compact.projection_nodes,
        },
    }


def _ast_node_overlaps_range(
    node: ast.AsyncFunctionDef | ast.ClassDef | ast.FunctionDef,
    start_line: int,
    end_line: int,
) -> bool:
    node_end_line = getattr(node, "end_lineno", node.lineno)
    return (
        isinstance(node_end_line, int)
        and node_end_line >= start_line
        and node.lineno <= end_line
    )
