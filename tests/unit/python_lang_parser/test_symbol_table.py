from __future__ import annotations

from python_lang_parser import parse_python_source


def test_parse_python_source_collects_native_symbol_table_bindings() -> None:
    report = parse_python_source(
        """
import os
VALUE = 1


def outer(x: int) -> int:
    y = x + VALUE

    def inner(z: int) -> int:
        return y + z

    return inner(1)
""",
        path="symbols.py",
    )

    assert report.is_valid
    assert [(scope.name, scope.kind, scope.parent_id) for scope in report.scopes] == [
        ("top", "module", None),
        ("outer", "function", report.scopes[0].id),
        ("inner", "function", report.scopes[1].id),
    ]

    bindings = {
        (binding.scope_name, binding.name): set(binding.flags)
        for binding in report.bindings
    }
    assert {"imported", "global", "local"} <= bindings[("top", "os")]
    assert {"assigned", "global", "local"} <= bindings[("top", "VALUE")]
    assert {"parameter", "local", "referenced"} <= bindings[("outer", "x")]
    assert {"assigned", "local"} <= bindings[("outer", "y")]
    assert {"global", "referenced"} <= bindings[("outer", "VALUE")]
    assert {"assigned", "local", "referenced", "namespace"} <= bindings[
        ("outer", "inner")
    ]
    assert {"free", "referenced"} <= bindings[("inner", "y")]
