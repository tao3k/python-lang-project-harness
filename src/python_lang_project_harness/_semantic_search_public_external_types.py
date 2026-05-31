"""Public API surfaces that expose external dependency types."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from ._semantic_search_common import (
    header,
)
from ._semantic_search_deps import (
    dependency_matches,
    normalize_dependency_name,
)
from ._semantic_search_model import MAX_SYMBOL_HITS
from ._semantic_search_owners import owners_for_paths
from ._semantic_search_packages import dependencies
from ._semantic_search_public_external_type_hits import public_external_type_hits
from ._semantic_search_view_hits import hit_next_actions

if TYPE_CHECKING:
    from python_lang_parser import (
        PythonReasoningTreeFacts,
    )

    from ._model import PythonHarnessReport


def public_external_types_payload(
    report: PythonHarnessReport,
    facts: PythonReasoningTreeFacts,
    project_root: Path,
    query: str,
) -> dict[str, Any]:
    """Build public external type/API payloads."""

    package = normalize_dependency_name(query.strip())
    manifest_matches = _manifest_matches(facts, package)
    hits = (
        []
        if not package
        else public_external_type_hits(report, project_root, package)[:MAX_SYMBOL_HITS]
    )
    owners = owners_for_paths(facts, project_root, [hit["ownerPath"] for hit in hits])
    confirmed = sum(1 for hit in hits if hit["reason"] == "public-external-type")
    possible = sum(
        1 for hit in hits if hit["reason"] == "possible-public-external-type"
    )
    return {
        "header": header(
            "public-external-types",
            {
                "q": query,
                "package": package,
                "manifest": len(manifest_matches),
                "own": len(owners),
                "hit": len(hits),
                "source": "native-parser",
                "view": "hits",
            },
        ),
        "nodes": [
            {
                "id": f"D:{package}",
                "kind": "dependency",
                "fields": {
                    "manifest": len(manifest_matches),
                    "confirmed": confirmed,
                    "possible": possible,
                },
            }
        ]
        if package
        else [],
        "owners": owners,
        "hits": hits,
        "nextActions": (
            ([] if not package else [{"kind": "dependency", "target": package}])
            + hit_next_actions(hits)
        )[:8],
        "notes": _public_external_type_notes(query, hits),
    }


def _manifest_matches(facts: PythonReasoningTreeFacts, package: str):
    return [item for item in dependencies(facts) if dependency_matches(item, package)]


def _public_external_type_notes(
    query: str,
    hits: list[dict[str, Any]],
) -> list[dict[str, str]]:
    if not query.strip():
        return [
            {
                "kind": "empty-query",
                "message": "public-external-types search requires a dependency package query",
            }
        ]
    if not hits:
        return [
            {
                "kind": "not-found",
                "message": f"public external type surfaces not found: {query}",
            }
        ]
    return []
