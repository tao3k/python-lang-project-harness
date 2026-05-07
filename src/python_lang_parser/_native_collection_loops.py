"""Parser-owned detection of collection and predicate loop idioms."""

from __future__ import annotations

import ast

from ._binding_mutations import _collection_mutation_names, _rebound_names

_COLLECTION_CONSTRUCTOR_NAMES = frozenset({"dict", "list", "set"})


def collection_bindings(statements: list[ast.stmt]) -> dict[str, str]:
    """Return active names bound to empty collection literals or constructors."""

    bindings: dict[str, str] = {}
    for statement in statements:
        bindings = updated_collection_bindings(bindings, statement)
    return bindings


def updated_collection_bindings(
    bindings: dict[str, str],
    statement: ast.stmt,
) -> dict[str, str]:
    """Return binding state after one statement executes."""

    invalidated_names = _rebound_names(statement) | _collection_mutation_names(
        statement
    )
    active_bindings = {
        name: kind for name, kind in bindings.items() if name not in invalidated_names
    }
    if (binding := empty_collection_binding(statement)) is None:
        return active_bindings
    name, kind = binding
    return active_bindings | {name: kind}


def manual_collection_loop_kind(
    statement: ast.stmt,
    bindings: dict[str, str],
) -> str | None:
    """Return the simple collection accumulator kind for one loop."""

    if not isinstance(statement, ast.For) or statement.orelse:
        return None
    return _collection_update_kind(statement.body, bindings)


def is_manual_predicate_loop_at(
    statements: list[ast.stmt],
    index: int,
) -> bool:
    """Return whether one loop spells a boolean predicate search."""

    if index + 1 >= len(statements):
        return False
    statement = statements[index]
    if not isinstance(statement, ast.For) or statement.orelse:
        return False
    loop_return = _single_if_boolean_return(statement.body)
    if loop_return is None:
        return False
    next_return = _boolean_return_value(statements[index + 1])
    return next_return is not None and next_return != loop_return


def empty_collection_binding(statement: ast.stmt) -> tuple[str, str] | None:
    """Return an empty collection binding as `(name, kind)` when present."""

    target_name, value = _single_collection_assignment(statement)
    if target_name is None or value is None:
        return None
    collection_kind = _empty_collection_kind(value)
    if collection_kind is None:
        return None
    return target_name, collection_kind


def _single_collection_assignment(
    statement: ast.stmt,
) -> tuple[str | None, ast.expr | None]:
    match statement:
        case ast.Assign(targets=[ast.Name(id=name)], value=value):
            return name, value
        case ast.AnnAssign(target=ast.Name(id=name), value=value):
            return name, value
        case _:
            return None, None


def _empty_collection_kind(expression: ast.expr) -> str | None:
    return _empty_literal_collection_kind(
        expression
    ) or _empty_constructor_collection_kind(expression)


def _empty_literal_collection_kind(expression: ast.expr) -> str | None:
    match expression:
        case ast.List(elts=[]):
            return "list"
        case ast.Set(elts=[]):
            return "set"
        case ast.Dict(keys=[]):
            return "dict"
        case _:
            return None


def _empty_constructor_collection_kind(expression: ast.expr) -> str | None:
    match expression:
        case ast.Call(func=ast.Name(id=name), args=[], keywords=[]) if (
            name in _COLLECTION_CONSTRUCTOR_NAMES
        ):
            return name
        case _:
            return None


def _collection_update_kind(
    statements: list[ast.stmt],
    bindings: dict[str, str],
) -> str | None:
    if len(statements) != 1:
        return None
    statement = statements[0]
    update_kind = _direct_collection_update_kind(statement, bindings)
    if update_kind is not None:
        return update_kind
    if isinstance(statement, ast.If) and not statement.orelse:
        return _collection_update_kind(statement.body, bindings)
    return None


def _direct_collection_update_kind(
    statement: ast.stmt,
    bindings: dict[str, str],
) -> str | None:
    if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call):
        return _collection_mutator_call_kind(statement.value, bindings)
    if isinstance(statement, ast.Assign):
        for target in statement.targets:
            if _is_dict_subscript_assignment(target, bindings):
                return "dict"
    return None


def _collection_mutator_call_kind(
    call: ast.Call,
    bindings: dict[str, str],
) -> str | None:
    if not isinstance(call.func, ast.Attribute):
        return None
    if not isinstance(call.func.value, ast.Name):
        return None
    collection_kind = bindings.get(call.func.value.id)
    if collection_kind == "list" and call.func.attr == "append":
        return "list"
    if collection_kind == "set" and call.func.attr == "add":
        return "set"
    return None


def _is_dict_subscript_assignment(
    target: ast.expr,
    bindings: dict[str, str],
) -> bool:
    return (
        isinstance(target, ast.Subscript)
        and isinstance(target.value, ast.Name)
        and bindings.get(target.value.id) == "dict"
    )


def _single_if_boolean_return(statements: list[ast.stmt]) -> bool | None:
    if len(statements) != 1 or not isinstance(statements[0], ast.If):
        return None
    statement = statements[0]
    if statement.orelse:
        return None
    return _single_boolean_return(statement.body)


def _single_boolean_return(statements: list[ast.stmt]) -> bool | None:
    if len(statements) != 1:
        return None
    return _boolean_return_value(statements[0])


def _boolean_return_value(statement: ast.stmt) -> bool | None:
    if not isinstance(statement, ast.Return):
        return None
    value = statement.value
    if isinstance(value, ast.Constant) and isinstance(value.value, bool):
        return value.value
    return None
