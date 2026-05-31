"""Semantic-search view dispatcher for Python packets."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from ._semantic_search_common import header
from ._semantic_search_hits import api_hits, callsite_hits, symbol_hits
from ._semantic_search_model import MAX_SYMBOL_HITS, PythonSemanticSearchOptions
from ._semantic_search_view_core import owner_payload, prime_payload, workspace_payload
from ._semantic_search_view_deps_imports import dependency_payload, import_payload
from ._semantic_search_view_hits import (
    generic_hits_payload,
    ingest_payload,
    tests_payload,
    text_payload,
)

if TYPE_CHECKING:
    from python_lang_parser import PythonReasoningTreeFacts

    from ._model import PythonHarnessReport


def payload_for_view(
    report: PythonHarnessReport,
    facts: PythonReasoningTreeFacts,
    project_root: Path,
    options: PythonSemanticSearchOptions,
) -> dict[str, Any]:
    """Dispatch one semantic-search view."""

    query = options.query or ""
    match options.view:
        case "workspace":
            return workspace_payload(report, facts, project_root)
        case "prime":
            return prime_payload(report, facts, project_root)
        case "owner":
            return owner_payload(report, facts, project_root, query)
        case "dependency" | "deps":
            return dependency_payload(report, facts, project_root, query)
        case "api":
            hits = api_hits(report, facts, project_root, query)[:MAX_SYMBOL_HITS]
            return generic_hits_payload("api", hits, facts, project_root, query)
        case "symbol":
            hits = symbol_hits(report, project_root, query)[:MAX_SYMBOL_HITS]
            return generic_hits_payload("symbol", hits, facts, project_root, query)
        case "callsite":
            hits = callsite_hits(report, project_root, query)[:MAX_SYMBOL_HITS]
            return generic_hits_payload("callsite", hits, facts, project_root, query)
        case "import":
            return import_payload(report, facts, project_root, query)
        case "tests":
            return tests_payload(report, facts, project_root, query)
        case "text":
            return text_payload(report, facts, project_root, query, options.pipes)
        case "ingest":
            return ingest_payload(facts, project_root, options.stdin)
        case _:
            return {
                "header": header(
                    options.view, {"error": f"unknown view {options.view}"}
                )
            }
