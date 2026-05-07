from __future__ import annotations

from python_lang_parser import PythonClassShape, PythonSymbolKind, parse_python_source


def test_parse_python_source_collects_symbols_imports_and_scopes() -> None:
    report = parse_python_source(
        '''
"""Module docs."""

import pathlib as path_mod
from collections import abc


@decorator("value")
class Runner(abc.ABC):
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
    assert [item.source_names for item in report.imports] == [
        ("pathlib",),
        ("abc",),
        ("json",),
    ]
    assert not any(item.is_wildcard for item in report.imports)
    assert [
        (
            symbol.kind,
            symbol.qualified_name,
            symbol.scope,
            symbol.decorators,
            symbol.base_classes,
            symbol.is_public,
            symbol.is_top_level,
        )
        for symbol in report.symbols
    ] == [
        (
            PythonSymbolKind.CLASS,
            "Runner",
            "",
            ("decorator('value')",),
            ("abc.ABC",),
            True,
            True,
        ),
        (
            PythonSymbolKind.ASYNC_FUNCTION,
            "Runner.run",
            "Runner",
            (),
            (),
            True,
            False,
        ),
    ]
    assert report.shape is not None
    assert report.shape.responsibility_groups == ("types",)
    assert report.shape.public_symbol_count == 1
    assert report.metadata["parser"] == "cpython.ast"
    assert report.metadata["parser_authority"] == "python-native"
    assert report.metadata["symbol_table"] == "cpython.symtable"
    assert report.export_candidates == ("Runner", "abc", "path_mod")
    assert report.source_line(2) == '"""Module docs."""'


def test_parse_python_source_collects_class_shape_visual_anchor_facts() -> None:
    report = parse_python_source(
        """
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, TypedDict


class ManualItem:
    def __init__(self, name: str, count: int) -> None:
        self.name = name
        self.count = count


@dataclass(frozen=True, slots=True)
class AnchoredItem:
    name: str
    count: int


class Payload(TypedDict):
    name: str
    count: int


class Closer(Protocol):
    def close(self) -> None: ...


class Mode(StrEnum):
    READ = "read"
""",
        path="models.py",
    )

    shapes = {
        symbol.name: symbol.class_shape
        for symbol in report.symbols
        if symbol.kind == PythonSymbolKind.CLASS
    }

    assert shapes["ManualItem"] == PythonClassShape(
        instance_field_count=2,
        init_self_assignment_count=2,
        method_count=1,
        dunder_method_count=1,
    )
    assert shapes["ManualItem"].is_manual_data_carrier
    assert shapes["AnchoredItem"].has_dataclass_anchor
    assert shapes["AnchoredItem"].has_visual_data_anchor
    assert shapes["Payload"].has_typed_dict_anchor
    assert shapes["Closer"].has_protocol_anchor
    assert shapes["Mode"].has_enum_anchor
