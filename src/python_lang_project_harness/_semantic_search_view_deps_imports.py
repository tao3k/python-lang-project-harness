"""Dependency and import semantic-search views for Python."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from ._semantic_search_common import header
from ._semantic_search_deps import (
    dependency_matches,
    dependency_node,
    dependency_query_parts,
    dependency_usage_hits,
    version_scope,
)
from ._semantic_search_hits import import_hits
from ._semantic_search_model import MAX_DEPENDENCY_HITS, MAX_IMPORT_HITS
from ._semantic_search_owners import import_edges, owners_for_paths
from ._semantic_search_packages import dependencies
from ._semantic_search_view_hits import hit_next_actions

if TYPE_CHECKING:
    from python_lang_parser import PythonReasoningTreeFacts

    from ._model import PythonHarnessReport


def dependency_payload(
    report: PythonHarnessReport,
    facts: PythonReasoningTreeFacts,
    project_root: Path,
    query: str,
) -> dict[str, Any]:
    """Build dependency/deps payloads."""

    parts = dependency_query_parts(query)
    matches = [
        item
        for item in dependencies(facts)
        if dependency_matches(item, parts["package"])
    ]
    usage_hits = dependency_usage_hits(report, project_root, parts["package"])
    nodes = [dependency_node(item, parts=parts) for item in matches]
    return {
        "header": header(
            "dependency",
            {
                "q": query,
                "manifest": len(nodes),
                "usage": len(usage_hits),
                "versionScope": version_scope(parts, matches),
            },
        ),
        "nodes": nodes[:MAX_DEPENDENCY_HITS],
        "hits": usage_hits[:MAX_DEPENDENCY_HITS],
        "nextActions": [
            {"kind": "api", "target": parts["apiQuery"] or parts["package"]}
        ],
        "notes": []
        if nodes or usage_hits
        else [{"kind": "not-found", "message": query}],
    }


def import_payload(
    report: PythonHarnessReport,
    facts: PythonReasoningTreeFacts,
    project_root: Path,
    query: str,
) -> dict[str, Any]:
    """Build import edge/search payloads."""

    hits = import_hits(report, project_root, query)[:MAX_IMPORT_HITS]
    edge_matches = _matching_import_edges(facts, project_root, query)
    paths = [hit["ownerPath"] for hit in hits] + _edge_owner_paths(edge_matches)
    return {
        "header": header(
            "import", {"q": query, "edge": len(edge_matches), "hit": len(hits)}
        ),
        "owners": owners_for_paths(facts, project_root, paths),
        "edges": edge_matches,
        "hits": hits,
        "nextActions": hit_next_actions(hits),
        "notes": []
        if edge_matches or hits
        else [{"kind": "not-found", "message": query}],
    }


def _matching_import_edges(
    facts: PythonReasoningTreeFacts,
    project_root: Path,
    query: str,
) -> list[dict[str, Any]]:
    query_folded = query.casefold()
    return [
        edge
        for edge in import_edges(facts, project_root, limit=MAX_IMPORT_HITS)
        if query_folded in edge["from"].casefold()
        or query_folded in edge["to"].casefold()
        or query_folded in str(edge.get("fields", {}).get("import", "")).casefold()
    ]


def _edge_owner_paths(edges: list[dict[str, Any]]) -> list[str]:
    paths: list[str] = []
    for edge in edges:
        paths.extend((edge["from"].removeprefix("O:"), edge["to"].removeprefix("O:")))
    return paths
