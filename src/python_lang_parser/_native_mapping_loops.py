"""Parser-owned detection of mapping count and group loop idioms."""

from __future__ import annotations

import ast


def manual_mapping_loop_kind(
    statement: ast.stmt,
    collection_bindings: dict[str, str],
) -> str | None:
    """Return the manual mapping loop kind for Counter/defaultdict advice."""

    if not isinstance(statement, ast.For) or statement.orelse:
        return None
    return _mapping_update_kind(statement.body, collection_bindings)


def _mapping_update_kind(
    statements: list[ast.stmt],
    collection_bindings: dict[str, str],
) -> str | None:
    match statements:
        case [
            ast.If() as guard,
            ast.AugAssign(op=ast.Add(), value=ast.Constant(value=1)) as update,
        ]:
            return _mapping_counter_kind(guard, update, collection_bindings)
        case [ast.If() as guard, ast.Expr(value=ast.Call() as update)]:
            return _mapping_group_kind(guard, update, collection_bindings)
        case _:
            return None


def _mapping_counter_kind(
    guard: ast.If,
    update: ast.AugAssign,
    collection_bindings: dict[str, str],
) -> str | None:
    binding = _missing_mapping_guard_binding(guard, collection_bindings)
    target = _mapping_subscript(update.target, collection_bindings)
    if binding is None or target is None:
        return None
    mapping_name, key = binding
    target_mapping, target_key = target
    if mapping_name == target_mapping and _same_expr(key, target_key):
        return "count"
    return None


def _mapping_group_kind(
    guard: ast.If,
    update: ast.Call,
    collection_bindings: dict[str, str],
) -> str | None:
    binding = _missing_mapping_guard_binding(guard, collection_bindings)
    target = _mapping_append_call_target(update, collection_bindings)
    if binding is None or target is None:
        return None
    mapping_name, key = binding
    target_mapping, target_key = target
    if mapping_name == target_mapping and _same_expr(key, target_key):
        return "group"
    return None


def _missing_mapping_guard_binding(
    guard: ast.If,
    collection_bindings: dict[str, str],
) -> tuple[str, ast.expr] | None:
    if guard.orelse:
        return None
    test_binding = _not_in_mapping_test(guard.test, collection_bindings)
    init_binding = _single_missing_mapping_init(guard.body, collection_bindings)
    if test_binding is None or init_binding is None:
        return None
    test_mapping, test_key = test_binding
    init_mapping, init_key = init_binding
    if test_mapping == init_mapping and _same_expr(test_key, init_key):
        return test_mapping, test_key
    return None


def _not_in_mapping_test(
    expression: ast.expr,
    collection_bindings: dict[str, str],
) -> tuple[str, ast.expr] | None:
    match expression:
        case ast.Compare(
            left=key,
            ops=[ast.NotIn()],
            comparators=[ast.Name(id=mapping_name)],
        ) if collection_bindings.get(mapping_name) == "dict":
            return mapping_name, key
        case _:
            return None


def _single_missing_mapping_init(
    statements: list[ast.stmt],
    collection_bindings: dict[str, str],
) -> tuple[str, ast.expr] | None:
    if len(statements) != 1:
        return None
    statement = statements[0]
    if not isinstance(statement, ast.Assign) or len(statement.targets) != 1:
        return None
    target = _mapping_subscript(statement.targets[0], collection_bindings)
    if target is None or not _is_counter_or_group_seed(statement.value):
        return None
    return target


def _is_counter_or_group_seed(expression: ast.expr) -> bool:
    return _is_zero_seed(expression) or _is_empty_list_seed(expression)


def _is_zero_seed(expression: ast.expr) -> bool:
    return isinstance(expression, ast.Constant) and expression.value == 0


def _is_empty_list_seed(expression: ast.expr) -> bool:
    return isinstance(expression, ast.List) and not expression.elts


def _mapping_append_call_target(
    call: ast.Call,
    collection_bindings: dict[str, str],
) -> tuple[str, ast.expr] | None:
    if call.args and not call.keywords:
        return _append_call_receiver(call, collection_bindings)
    return None


def _append_call_receiver(
    call: ast.Call,
    collection_bindings: dict[str, str],
) -> tuple[str, ast.expr] | None:
    match call.func:
        case ast.Attribute(value=receiver, attr="append"):
            return _mapping_subscript(receiver, collection_bindings)
        case _:
            return None


def _mapping_subscript(
    expression: ast.expr,
    collection_bindings: dict[str, str],
) -> tuple[str, ast.expr] | None:
    match expression:
        case ast.Subscript(value=ast.Name(id=mapping_name), slice=key) if (
            collection_bindings.get(mapping_name) == "dict"
        ):
            return mapping_name, key
        case _:
            return None


def _same_expr(left: ast.expr, right: ast.expr) -> bool:
    return ast.dump(left, include_attributes=False) == ast.dump(
        right,
        include_attributes=False,
    )
