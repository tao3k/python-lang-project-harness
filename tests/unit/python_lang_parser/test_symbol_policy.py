from __future__ import annotations

from python_lang_parser import (
    parse_python_source,
    python_assignment_is_public_top_level,
    python_symbol_is_callable,
    python_symbol_is_class,
    python_symbol_is_public_callable,
    python_symbol_is_public_callable_boundary,
    python_symbol_is_public_class,
    python_symbol_is_public_top_level,
    python_symbol_is_test_function,
)


def test_python_symbol_role_helpers_are_parser_owned() -> None:
    report = parse_python_source(
        """
class Service:
    def run(self):
        return None


class _Private:
    def method(self):
        return None


def helper():
    return None


def _hidden():
    return None


def test_sync():
    return None


async def test_async():
    return None
""",
        path="test_roles.py",
    )

    symbols = {symbol.qualified_name: symbol for symbol in report.symbols}

    assert python_symbol_is_class(symbols["Service"])
    assert python_symbol_is_public_class(symbols["Service"])
    assert not python_symbol_is_public_class(symbols["_Private"])
    assert python_symbol_is_public_top_level(symbols["Service"])
    assert not python_symbol_is_public_top_level(symbols["Service.run"])
    assert python_symbol_is_callable(symbols["helper"])
    assert python_symbol_is_public_callable(symbols["helper"])
    assert not python_symbol_is_public_callable(symbols["_hidden"])
    assert python_symbol_is_public_callable(symbols["_Private.method"])
    assert python_symbol_is_public_callable_boundary(
        symbols["helper"],
        public_class_scopes=frozenset({"Service"}),
    )
    assert python_symbol_is_public_callable_boundary(
        symbols["Service.run"],
        public_class_scopes=frozenset({"Service"}),
    )
    assert not python_symbol_is_public_callable_boundary(
        symbols["_Private.method"],
        public_class_scopes=frozenset({"Service"}),
    )
    assert python_symbol_is_test_function(symbols["test_sync"])
    assert python_symbol_is_test_function(symbols["test_async"])
    assert not python_symbol_is_test_function(symbols["helper"])


def test_python_assignment_role_helpers_are_parser_owned() -> None:
    report = parse_python_source(
        """
VALUE = 1
_HIDDEN = 2


def build():
    local = 3
    return local
""",
        path="assignments.py",
    )

    assignments = {
        (assignment.scope, assignment.name): assignment
        for assignment in report.assignments
    }

    assert python_assignment_is_public_top_level(assignments[("", "VALUE")])
    assert not python_assignment_is_public_top_level(assignments[("", "_HIDDEN")])
    assert not python_assignment_is_public_top_level(assignments[("build", "local")])
