"""Parser-local binding mutation helpers for linear statement passes."""

from __future__ import annotations

import ast as _ast
from collections.abc import Iterator as _Iterator

_COLLECTION_MUTATOR_NAMES = frozenset(
    {
        "add",
        "append",
        "clear",
        "discard",
        "extend",
        "insert",
        "pop",
        "remove",
        "reverse",
        "setdefault",
        "sort",
        "update",
    }
)


def _rebound_names(statement: _ast.stmt) -> frozenset[str]:
    """Return names rebound by a statement without entering nested definitions."""

    return frozenset(
        name
        for child in _statement_family(statement)
        for name in _statement_rebound_names(child)
    )


def _collection_mutation_names(statement: _ast.stmt) -> frozenset[str]:
    """Return collection binding names mutated by a statement."""

    return frozenset(
        name
        for child in _statement_family(statement)
        for name in _statement_collection_mutation_names(child)
    )


def _statement_family(statement: _ast.stmt) -> _Iterator[_ast.stmt]:
    yield statement
    for child in _child_statements(statement):
        yield from _statement_family(child)


def _child_statements(statement: _ast.stmt) -> _Iterator[_ast.stmt]:
    match statement:
        case (
            _ast.For(body=body, orelse=orelse)
            | _ast.AsyncFor(body=body, orelse=orelse)
            | _ast.If(body=body, orelse=orelse)
            | _ast.While(body=body, orelse=orelse)
        ):
            yield from body
            yield from orelse
        case _ast.With(body=body) | _ast.AsyncWith(body=body):
            yield from body
        case (
            _ast.Try(body=body, handlers=handlers, orelse=orelse, finalbody=finalbody)
            | _ast.TryStar(
                body=body,
                handlers=handlers,
                orelse=orelse,
                finalbody=finalbody,
            )
        ):
            yield from body
            for handler in handlers:
                yield from handler.body
            yield from orelse
            yield from finalbody
        case _ast.Match(cases=cases):
            for case in cases:
                yield from case.body
        case _:
            return


def _statement_rebound_names(statement: _ast.stmt) -> _Iterator[str]:
    match statement:
        case _ast.Assign(targets=targets):
            for target in targets:
                yield from _target_names(target)
        case _ast.AnnAssign(target=target, value=value) if value is not None:
            yield from _target_names(target)
        case _ast.AugAssign(target=target):
            yield from _target_names(target)
        case _ast.For(target=target) | _ast.AsyncFor(target=target):
            yield from _target_names(target)
        case _ast.With(items=items) | _ast.AsyncWith(items=items):
            for item in items:
                if item.optional_vars is not None:
                    yield from _target_names(item.optional_vars)
        case _:
            return


def _statement_collection_mutation_names(statement: _ast.stmt) -> _Iterator[str]:
    match statement:
        case _ast.Assign(targets=targets):
            for target in targets:
                yield from _target_collection_roots(target)
        case _ast.AnnAssign(target=target, value=value) if value is not None:
            yield from _target_collection_roots(target)
        case _ast.AugAssign(target=target):
            yield from _target_collection_roots(target)
        case _ast.Expr(value=_ast.Call() as call):
            if (name := _mutator_receiver_name(call)) is not None:
                yield name
        case _:
            return


def _target_names(target: _ast.expr) -> _Iterator[str]:
    match target:
        case _ast.Name(id=name):
            yield name
        case _ast.Tuple(elts=elts) | _ast.List(elts=elts):
            for element in elts:
                yield from _target_names(element)
        case _ast.Starred(value=value):
            yield from _target_names(value)
        case _:
            return


def _target_collection_roots(target: _ast.expr) -> _Iterator[str]:
    match target:
        case _ast.Subscript(value=value):
            if (name := _collection_receiver_name(value)) is not None:
                yield name
        case _ast.Tuple(elts=elts) | _ast.List(elts=elts):
            for element in elts:
                yield from _target_collection_roots(element)
        case _ast.Starred(value=value):
            yield from _target_collection_roots(value)
        case _:
            return


def _mutator_receiver_name(call: _ast.Call) -> str | None:
    match call.func:
        case _ast.Attribute(value=receiver, attr=attr) if (
            attr in _COLLECTION_MUTATOR_NAMES
        ):
            return _collection_receiver_name(receiver)
        case _:
            return None


def _collection_receiver_name(expression: _ast.expr) -> str | None:
    match expression:
        case _ast.Name(id=name):
            return name
        case _ast.Subscript(value=value):
            return _collection_receiver_name(value)
        case _:
            return None
