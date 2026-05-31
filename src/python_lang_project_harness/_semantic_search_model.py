"""Shared semantic-search model aliases for the Python provider."""

from __future__ import annotations

from dataclasses import dataclass

FieldValue = str | int | float | bool | list[str | int | float | bool]
Fields = dict[str, FieldValue]

MAX_PRIME_OWNERS = 12
MAX_PRIME_EDGES = 24
MAX_WORKSPACE_PACKAGES = 24
MAX_WORKSPACE_EDGES = 32
MAX_FINDINGS = 8
MAX_TEXT_HITS = 20
MAX_SYMBOL_HITS = 20
MAX_IMPORT_HITS = 30
MAX_DEPENDENCY_HITS = 24
MAX_TEST_HITS = 24


@dataclass(frozen=True, slots=True)
class PythonSemanticSearchOptions:
    """Options parsed from a `py-harness search` invocation."""

    view: str
    query: str | None = None
    pipes: tuple[str, ...] = ()
    render_mode: str | None = None
    stdin: str = ""
