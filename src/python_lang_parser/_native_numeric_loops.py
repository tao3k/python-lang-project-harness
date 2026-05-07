"""Parser-owned detection of numeric accumulation loop idioms."""

from __future__ import annotations

import ast

from ._binding_mutations import _rebound_names


def numeric_accumulator_bindings(statements: list[ast.stmt]) -> frozenset[str]:
    """Return active names initialized as numeric accumulators in one block."""

    bindings = frozenset[str]()
    for statement in statements:
        bindings = updated_numeric_accumulator_bindings(bindings, statement)
    return bindings


def updated_numeric_accumulator_bindings(
    bindings: frozenset[str],
    statement: ast.stmt,
) -> frozenset[str]:
    """Return numeric accumulator binding state after one statement executes."""

    active_bindings = bindings - _rebound_names(statement)
    if (name := _zero_number_binding(statement)) is None:
        return active_bindings
    return active_bindings | {name}


def is_manual_numeric_sum_loop(
    statement: ast.stmt,
    accumulator_names: frozenset[str],
) -> bool:
    """Return whether a loop spells a simple sum-style accumulation."""

    if not isinstance(statement, ast.For) or statement.orelse:
        return False
    return _single_numeric_add_update(statement.body, accumulator_names)


def _zero_number_binding(statement: ast.stmt) -> str | None:
    target_name, value = _single_assignment(statement)
    if target_name is None or not _is_zero_number(value):
        return None
    return target_name


def _single_assignment(statement: ast.stmt) -> tuple[str | None, ast.expr | None]:
    match statement:
        case ast.Assign(targets=[ast.Name(id=name)], value=value):
            return name, value
        case ast.AnnAssign(target=ast.Name(id=name), value=value):
            return name, value
        case _:
            return None, None


def _is_zero_number(expression: ast.expr | None) -> bool:
    return (
        isinstance(expression, ast.Constant)
        and isinstance(expression.value, int | float)
        and expression.value == 0
    )


def _single_numeric_add_update(
    statements: list[ast.stmt],
    accumulator_names: frozenset[str],
) -> bool:
    match statements:
        case [ast.AugAssign(target=ast.Name(id=name), op=ast.Add())]:
            return name in accumulator_names
        case [ast.If(orelse=[]) as guard]:
            return _single_numeric_add_update(guard.body, accumulator_names)
        case _:
            return False
