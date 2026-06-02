from __future__ import annotations

import ast


def _args(args: ast.arguments) -> str:
    return _expr(args)


def _targets(targets: list[ast.expr]) -> str:
    return ", ".join(_expr(target) for target in targets)


def _with_items(items: list[ast.withitem]) -> str:
    rendered: list[str] = []
    for item in items:
        optional = (
            f" as {_expr(item.optional_vars)}" if item.optional_vars is not None else ""
        )
        rendered.append(f"{_expr(item.context_expr)}{optional}")
    return ", ".join(rendered)


def _aug_assign_stmt(node: ast.AugAssign) -> str:
    return f"{_expr(node.target)} {_aug_operator(node.op)}= {_expr(node.value)}"


def _import_stmt(node: ast.Import | ast.ImportFrom) -> str:
    if isinstance(node, ast.Import):
        return "import " + ", ".join(alias.name for alias in node.names)
    module = "." * node.level + (node.module or "")
    return f"from {module} import " + ", ".join(alias.name for alias in node.names)


def _expr(node: ast.AST | None) -> str:
    if node is None:
        return ""
    try:
        text = ast.unparse(node)
    except Exception:
        text = node.__class__.__name__
    return _limit_expr(" ".join(text.split()))


def _limit_expr(text: str, *, max_chars: int = 120) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "..."


def _aug_operator(op: ast.operator) -> str:
    operators = {
        ast.Add: "+",
        ast.Sub: "-",
        ast.Mult: "*",
        ast.MatMult: "@",
        ast.Div: "/",
        ast.Mod: "%",
        ast.Pow: "**",
        ast.LShift: "<<",
        ast.RShift: ">>",
        ast.BitOr: "|",
        ast.BitXor: "^",
        ast.BitAnd: "&",
        ast.FloorDiv: "//",
    }
    return operators.get(type(op), op.__class__.__name__)
