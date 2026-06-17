"""Native AST name and source helpers."""

from __future__ import annotations

import ast

from ._name_policy import python_name_is_public

_ast_splitlines_no_ff = getattr(ast, "_splitlines_no_ff", None)
_START_COLUMN_FIELD = "_".join(("col", "offset"))
_END_COLUMN_FIELD = "_".join(("end", "col", "offset"))


def unparse(node: ast.AST) -> str:
    """Return a compact Python expression for an AST node."""

    try:
        return ast.unparse(node)
    except Exception:  # pragma: no cover - defensive fallback for exotic AST nodes.
        return node.__class__.__name__


def qualified_expr_name(node: ast.AST) -> str:
    """Return the parser-recognized dotted name for an expression."""

    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = qualified_expr_name(node.value)
        if base:
            return f"{base}.{node.attr}"
        return node.attr
    if isinstance(node, ast.Call):
        return qualified_expr_name(node.func)
    if isinstance(node, ast.Subscript):
        return qualified_expr_name(node.value)
    return unparse(node)


def source_segment(source: str, node: ast.AST) -> str | None:
    """Return the source segment for an AST node when CPython exposes it."""

    try:
        return ast.get_source_segment(source, node)
    except Exception:  # pragma: no cover - defensive fallback for exotic AST nodes.
        return None


class SourceSegmentLookup:
    """Cache parser-style source lines for repeated AST source slices."""

    def __init__(self, source: str) -> None:
        self._lines = _splitlines_no_form_feed(source)

    def segment(self, node: ast.AST) -> str | None:
        """Return the source segment for an AST node from cached source lines."""

        try:
            end_lineno_value = getattr(node, "end_lineno", None)
            end_column_value = end_column(node)
            if end_lineno_value is None or end_column_value is None:
                return None
            lineno = node.lineno - 1
            end_lineno = end_lineno_value - 1
            start_column = getattr(node, _START_COLUMN_FIELD)
        except AttributeError:
            return None
        if lineno < 0 or end_lineno >= len(self._lines):
            return None
        try:
            if end_lineno == lineno:
                return _slice_parser_columns(
                    self._lines[lineno], start_column, end_column_value
                )
            first = _slice_parser_columns(self._lines[lineno], start_column, None)
            last = _slice_parser_columns(
                self._lines[end_lineno], None, end_column_value
            )
            return "".join((first, *self._lines[lineno + 1 : end_lineno], last))
        except UnicodeDecodeError:  # pragma: no cover - mirrors ast fallback behavior.
            return None


def _splitlines_no_form_feed(source: str) -> list[str]:
    if callable(_ast_splitlines_no_ff):
        return _ast_splitlines_no_ff(source, None)
    return source.splitlines(keepends=True)


def _slice_parser_columns(
    line: str,
    start: int | None,
    end: int | None,
) -> str:
    return line.encode()[start:end].decode()


def iter_assignment_target_nodes(target: ast.AST) -> tuple[ast.AST, ...]:
    """Return concrete name-like target nodes from an assignment target."""

    if isinstance(target, ast.Starred):
        return iter_assignment_target_nodes(target.value)
    if isinstance(target, ast.Tuple | ast.List):
        nodes: list[ast.AST] = []
        for element in target.elts:
            nodes.extend(iter_assignment_target_nodes(element))
        return tuple(nodes)
    if isinstance(target, ast.Name | ast.Attribute | ast.Subscript):
        return (target,)
    return ()


def target_assigns_name(target: ast.AST, name: str) -> bool:
    """Return whether an assignment target binds one exact name."""

    return any(
        isinstance(item, ast.Name) and item.id == name
        for item in iter_assignment_target_nodes(target)
    )


def is_public_name(name: str) -> bool:
    """Return whether a parser-visible name is part of public project surface."""

    return python_name_is_public(name)


def expr_context(context: ast.expr_context) -> str:
    """Return a compact expression-context label."""

    if isinstance(context, ast.Load):
        return "load"
    if isinstance(context, ast.Store):
        return "store"
    if isinstance(context, ast.Del):
        return "del"
    return context.__class__.__name__.lower()


def end_line(node: ast.AST) -> int | None:
    """Return the native AST end line when available."""

    return getattr(node, "end_lineno", None)


def end_column(node: ast.AST) -> int | None:
    """Return the native AST end column when available."""

    return getattr(node, _END_COLUMN_FIELD, None)
