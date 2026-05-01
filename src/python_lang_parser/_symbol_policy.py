"""Python symbol role helpers shared by parser consumers."""

from __future__ import annotations

from ._name_policy import python_scope_is_public
from ._symbol_model import PythonAssignmentTarget, PythonSymbol, PythonSymbolKind


def python_symbol_is_callable(symbol: PythonSymbol) -> bool:
    """Return whether a parser symbol is a synchronous or async callable."""

    return symbol.kind in {PythonSymbolKind.FUNCTION, PythonSymbolKind.ASYNC_FUNCTION}


def python_symbol_is_class(symbol: PythonSymbol) -> bool:
    """Return whether a parser symbol is a class definition."""

    return symbol.kind == PythonSymbolKind.CLASS


def python_symbol_is_public_callable(symbol: PythonSymbol) -> bool:
    """Return whether a parser symbol exposes a public callable name."""

    return python_symbol_is_callable(symbol) and symbol.is_public


def python_symbol_is_public_class(symbol: PythonSymbol) -> bool:
    """Return whether a parser symbol exposes a public class boundary."""

    return (
        python_symbol_is_class(symbol)
        and symbol.is_public
        and python_scope_is_public(symbol.scope)
    )


def python_symbol_is_public_top_level(symbol: PythonSymbol) -> bool:
    """Return whether a parser symbol belongs to top-level public surface."""

    return symbol.is_top_level and symbol.is_public


def python_assignment_is_public_top_level(
    assignment: PythonAssignmentTarget,
) -> bool:
    """Return whether an assignment belongs to top-level public surface."""

    return assignment.is_top_level and assignment.is_public


def python_symbol_is_public_callable_boundary(
    symbol: PythonSymbol,
    *,
    public_class_scopes: frozenset[str],
) -> bool:
    """Return whether a callable symbol is part of a public API boundary."""

    return python_symbol_is_public_callable(symbol) and (
        symbol.scope == "" or symbol.scope in public_class_scopes
    )


def python_symbol_is_test_function(symbol: PythonSymbol) -> bool:
    """Return whether a parser symbol is a pytest-style test function."""

    return python_symbol_is_callable(symbol) and symbol.name.startswith("test_")
