from __future__ import annotations

from python_lang_parser import (
    PythonCallEffect,
    PythonReferenceKind,
    parse_python_source,
)


def test_parse_python_source_collects_agent_reference_and_call_index() -> None:
    report = parse_python_source(
        """
def build(client, items):
    for item in items:
        client.worker.process(item, flag=True)
    return helper(client.worker.status)
""",
        path="calls.py",
    )

    assert report.is_valid
    assert [
        (
            call.function,
            call.scope,
            call.positional_count,
            call.keyword_names,
            call.effect,
            call.expression,
        )
        for call in report.calls
    ] == [
        (
            "client.worker.process",
            "build",
            1,
            ("flag",),
            PythonCallEffect.UNKNOWN,
            "client.worker.process(item, flag=True)",
        ),
        (
            "helper",
            "build",
            1,
            (),
            PythonCallEffect.UNKNOWN,
            "helper(client.worker.status)",
        ),
    ]

    references = {
        (reference.kind, reference.name, reference.context, reference.scope)
        for reference in report.references
    }
    assert (PythonReferenceKind.NAME, "item", "store", "build") in references
    assert (PythonReferenceKind.NAME, "items", "load", "build") in references
    assert (
        PythonReferenceKind.ATTRIBUTE,
        "client.worker.process",
        "load",
        "build",
    ) in references
    assert (
        PythonReferenceKind.ATTRIBUTE,
        "client.worker.status",
        "load",
        "build",
    ) in references
    serialized = report.to_dict()
    assert serialized["references"]
    assert serialized["calls"][0]["function"] == "client.worker.process"
    assert serialized["calls"][0]["effect"] == "unknown"


def test_parse_python_source_classifies_wildcard_import_and_builtin_call_effects() -> (
    None
):
    report = parse_python_source(
        """
from tools import *


def run() -> None:
    print("debug")
    breakpoint()
""",
        path="effects.py",
    )

    assert report.is_valid
    assert [(item.names, item.is_wildcard) for item in report.imports] == [
        (("*",), True),
    ]
    assert [(call.function, call.effect) for call in report.calls] == [
        ("print", PythonCallEffect.STANDARD_OUTPUT),
        ("breakpoint", PythonCallEffect.DEBUG_BREAKPOINT),
    ]
