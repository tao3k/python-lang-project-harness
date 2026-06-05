"""Native Python AST projection into tree-sitter-compatible captures."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import TYPE_CHECKING

from ._python_compact import compact_python_item
from ._python_expr import _expr
from ._semantic_search_common import display_path
from ._tree_sitter_query_model import (
    LEAF_TREE_SITTER_QUERY_NODES,
    MAX_SYNTAX_QUERY_ROWS,
    SUPPORTED_TREE_SITTER_QUERY_NODES,
    SyntaxQueryProjection,
    SyntaxQueryRow,
    SyntaxQuerySelector,
    node_span,
    selector_matches,
    terms_match,
    tree_sitter_query_nodes,
)

if TYPE_CHECKING:
    from python_lang_parser import PythonModuleReport

    from ._model import PythonHarnessReport


def project_tree_sitter_query(
    report: PythonHarnessReport,
    project_root: Path,
    query_source: str,
    captures: tuple[str, ...],
    terms: list[str],
    selector: SyntaxQuerySelector | None,
) -> SyntaxQueryProjection:
    requested_nodes = tree_sitter_query_nodes(query_source)
    unsupported_nodes = sorted(
        node
        for node in requested_nodes
        if node not in SUPPORTED_TREE_SITTER_QUERY_NODES
        and node not in LEAF_TREE_SITTER_QUERY_NODES
    )
    active_nodes = requested_nodes & SUPPORTED_TREE_SITTER_QUERY_NODES
    rows: list[SyntaxQueryRow] = []
    for module in report.modules:
        rows.extend(
            _module_syntax_query_rows(
                module, project_root, active_nodes, captures, terms, selector
            )
        )
    rows.sort(key=lambda row: (row.path, row.item_start_line, row.start_line, row.name))
    selected = rows[:MAX_SYNTAX_QUERY_ROWS]
    return SyntaxQueryProjection(
        rows=selected,
        total_matches=len(rows),
        truncated=len(rows) > len(selected),
        unsupported_nodes=unsupported_nodes,
    )


def _module_syntax_query_rows(
    module: PythonModuleReport,
    project_root: Path,
    active_nodes: frozenset[str],
    captures: tuple[str, ...],
    terms: list[str],
    selector: SyntaxQuerySelector | None,
) -> list[SyntaxQueryRow]:
    if module.path is None:
        return []
    owner_path = display_path(module.path, project_root)
    if selector is not None and selector.path != owner_path:
        return []
    try:
        tree = ast.parse("\n".join(module.source_lines))
    except SyntaxError:
        return []
    rows: list[SyntaxQueryRow] = []
    for node in ast.walk(tree):
        row = _row_for_ast_node(module, owner_path, active_nodes, captures, node)
        if row is not None:
            rows.append(row)
        rows.extend(
            _rows_for_ast_node_extras(module, owner_path, active_nodes, captures, node)
        )
    return [
        row
        for row in rows
        if selector_matches(row, selector) and terms_match(row, terms)
    ]


def _row_for_ast_node(
    module: PythonModuleReport,
    owner_path: str,
    active_nodes: frozenset[str],
    captures: tuple[str, ...],
    node: ast.AST,
) -> SyntaxQueryRow | None:
    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
        if "function_definition" not in active_nodes:
            return None
        return _syntax_row(
            module,
            owner_path,
            capture=_first_capture(captures, "function.name", "function.definition"),
            node_type="function_definition",
            name=node.name,
            node=node,
            item_node=node,
        )
    if isinstance(node, ast.ClassDef):
        if "class_definition" not in active_nodes:
            return None
        return _syntax_row(
            module,
            owner_path,
            capture=_first_capture(captures, "class.name", "class.definition"),
            node_type="class_definition",
            name=node.name,
            node=node,
            item_node=node,
        )
    if isinstance(node, ast.Call) and "call" in active_nodes:
        return _syntax_row(
            module,
            owner_path,
            capture=_call_capture(captures, node),
            node_type="call",
            name=_expr(node.func),
            node=node,
            item_node=node,
        )
    return _import_or_control_row(module, owner_path, active_nodes, captures, node)


def _rows_for_ast_node_extras(
    module: PythonModuleReport,
    owner_path: str,
    active_nodes: frozenset[str],
    captures: tuple[str, ...],
    node: ast.AST,
) -> list[SyntaxQueryRow]:
    rows: list[SyntaxQueryRow] = []
    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
        if "decorator" in active_nodes or "decorated_definition" in active_nodes:
            rows.extend(
                _decorator_rows(module, owner_path, captures, node, node.decorator_list)
            )
    if isinstance(node, ast.Call) and "keyword_argument" in active_nodes:
        rows.extend(_keyword_rows(module, owner_path, captures, node))
    return rows


def _decorator_rows(
    module: PythonModuleReport,
    owner_path: str,
    captures: tuple[str, ...],
    item_node: ast.AST,
    decorators: list[ast.expr],
) -> list[SyntaxQueryRow]:
    rows: list[SyntaxQueryRow] = []
    for decorator in decorators:
        row = _syntax_row(
            module,
            owner_path,
            capture=_decorator_capture(captures, decorator),
            node_type="decorator",
            name=_expr(decorator),
            node=decorator,
            item_node=item_node,
        )
        if row is not None:
            rows.append(row)
    return rows


def _keyword_rows(
    module: PythonModuleReport,
    owner_path: str,
    captures: tuple[str, ...],
    call: ast.Call,
) -> list[SyntaxQueryRow]:
    rows: list[SyntaxQueryRow] = []
    for keyword in call.keywords:
        if keyword.arg is None:
            continue
        row = _syntax_row(
            module,
            owner_path,
            capture=_first_capture(captures, "call.keyword"),
            node_type="keyword_argument",
            name=keyword.arg,
            node=keyword.value,
            item_node=call,
        )
        if row is not None:
            rows.append(row)
    return rows


def _import_or_control_row(
    module: PythonModuleReport,
    owner_path: str,
    active_nodes: frozenset[str],
    captures: tuple[str, ...],
    node: ast.AST,
) -> SyntaxQueryRow | None:
    if isinstance(node, ast.Import) and "import_statement" in active_nodes:
        return _syntax_row(
            module,
            owner_path,
            capture=_first_capture(captures, "import.name", "import.declaration"),
            node_type="import_statement",
            name=", ".join(alias.asname or alias.name for alias in node.names),
            node=node,
            item_node=node,
        )
    if isinstance(node, ast.ImportFrom) and "import_from_statement" in active_nodes:
        return _import_from_row(module, owner_path, captures, node)
    control = _control_row_spec(active_nodes, captures, node)
    if control is None:
        return None
    node_type, capture, name_node = control
    return _syntax_row(
        module,
        owner_path,
        capture=capture,
        node_type=node_type,
        name=_expr(name_node),
        node=name_node,
        item_node=node,
    )


def _import_from_row(
    module: PythonModuleReport,
    owner_path: str,
    captures: tuple[str, ...],
    node: ast.ImportFrom,
) -> SyntaxQueryRow | None:
    module_name = "." * node.level + (node.module or "")
    imported = ", ".join(alias.asname or alias.name for alias in node.names)
    name = f"{module_name}:{imported}" if module_name else imported
    return _syntax_row(
        module,
        owner_path,
        capture=_first_capture(
            captures, "import.name", "import.path", "import.declaration"
        ),
        node_type="import_from_statement",
        name=name,
        node=node,
        item_node=node,
    )


def _control_row_spec(
    active_nodes: frozenset[str],
    captures: tuple[str, ...],
    node: ast.AST,
) -> tuple[str, str | None, ast.AST] | None:
    if isinstance(node, ast.If) and "if_statement" in active_nodes:
        return (
            "if_statement",
            _first_capture(captures, "control.condition", "control.if"),
            node.test,
        )
    if isinstance(node, ast.For | ast.AsyncFor) and "for_statement" in active_nodes:
        return (
            "for_statement",
            _first_capture(captures, "control.loop", "control.iterable"),
            node.iter,
        )
    if isinstance(node, ast.While) and "while_statement" in active_nodes:
        return (
            "while_statement",
            _first_capture(captures, "control.condition", "control.loop"),
            node.test,
        )
    if isinstance(node, ast.With | ast.AsyncWith) and "with_statement" in active_nodes:
        target = node.items[0].context_expr if node.items else node
        return (
            "with_statement",
            _first_capture(captures, "context.manager", "control.with"),
            target,
        )
    if isinstance(node, ast.Try) and "try_statement" in active_nodes:
        return ("try_statement", _first_capture(captures, "control.exception"), node)
    if isinstance(node, ast.Match) and "match_statement" in active_nodes:
        return (
            "match_statement",
            _first_capture(captures, "control.subject", "control.match"),
            node.subject,
        )
    return None


def _syntax_row(
    module: PythonModuleReport,
    owner_path: str,
    *,
    capture: str | None,
    node_type: str,
    name: str,
    node: ast.AST,
    item_node: ast.AST,
) -> SyntaxQueryRow | None:
    if capture is None:
        return None
    start_line, end_line = node_span(node)
    item_start_line, item_end_line = node_span(item_node)
    return SyntaxQueryRow(
        capture=capture,
        node=node_type,
        name=name,
        path=owner_path,
        start_line=start_line,
        end_line=end_line,
        item_start_line=item_start_line,
        item_end_line=item_end_line,
        item_code=_compact_item_code(
            module, owner_path, item_start_line, item_end_line
        ),
    )


def _compact_item_code(
    module: PythonModuleReport,
    owner_path: str,
    start_line: int,
    end_line: int,
) -> str:
    raw_lines = module.source_lines[start_line - 1 : end_line]
    return compact_python_item(raw_lines, owner_path, start_line).code


def _first_capture(captures: tuple[str, ...], *preferred: str) -> str | None:
    for capture in preferred:
        if capture in captures:
            return capture
    return captures[0] if captures else None


def _call_capture(captures: tuple[str, ...], node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Attribute):
        capture = _first_capture(captures, "call.method", "call.target")
        if capture is not None:
            return capture
    return _first_capture(captures, "call.target", "call.expression")


def _decorator_capture(captures: tuple[str, ...], node: ast.AST) -> str | None:
    if isinstance(node, ast.Call):
        capture = _first_capture(captures, "decorator.call", "decorator.expression")
        if capture is not None:
            return capture
    return _first_capture(captures, "decorator.expression", "decorator.target")
