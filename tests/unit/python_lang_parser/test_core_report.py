from __future__ import annotations

from python_lang_parser import PythonSymbolKind, parse_python_source


def test_parse_python_source_collects_symbols_imports_and_scopes() -> None:
    report = parse_python_source(
        '''
"""Module docs."""

import pathlib as path_mod
from collections import abc


@decorator("value")
class Runner:
    """Runner docs."""

    async def run(self) -> None:
        import json
        return None
''',
        path="runner.py",
    )

    assert report.is_valid
    assert report.module_docstring == "Module docs."
    assert [(item.module, item.names, item.scope) for item in report.imports] == [
        (None, ("path_mod",), ""),
        ("collections", ("abc",), ""),
        (None, ("json",), "Runner.run"),
    ]
    assert not any(item.is_wildcard for item in report.imports)
    assert [
        (
            symbol.kind,
            symbol.qualified_name,
            symbol.scope,
            symbol.decorators,
            symbol.is_public,
            symbol.is_top_level,
        )
        for symbol in report.symbols
    ] == [
        (PythonSymbolKind.CLASS, "Runner", "", ("decorator('value')",), True, True),
        (PythonSymbolKind.ASYNC_FUNCTION, "Runner.run", "Runner", (), True, False),
    ]
    assert report.shape is not None
    assert report.shape.responsibility_groups == ("types",)
    assert report.shape.public_symbol_count == 1
    assert report.metadata["parser"] == "cpython.ast"
    assert report.metadata["parser_authority"] == "python-native"
    assert report.metadata["symbol_table"] == "cpython.symtable"
    assert report.export_candidates == ("Runner", "abc", "path_mod")
    assert report.source_line(2) == '"""Module docs."""'
