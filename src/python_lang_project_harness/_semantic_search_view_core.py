"""Core workspace, prime, and owner semantic-search views."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from ._semantic_search_common import header, path_hit
from ._semantic_search_deps import dependency_node
from ._semantic_search_findings import finding_facts
from ._semantic_search_model import (
    MAX_DEPENDENCY_HITS,
    MAX_IMPORT_HITS,
    MAX_PRIME_EDGES,
    MAX_PRIME_OWNERS,
    MAX_WORKSPACE_EDGES,
)
from ._semantic_search_owners import (
    import_edges,
    matching_owner_nodes,
    owner_nodes,
    owner_record,
    ranked_owner_records,
)
from ._semantic_search_packages import dependencies, project_name, workspace_packages

if TYPE_CHECKING:
    from python_lang_parser import PythonReasoningTreeFacts

    from ._model import PythonHarnessReport


def workspace_payload(
    report: PythonHarnessReport,
    facts: PythonReasoningTreeFacts,
    project_root: Path,
) -> dict[str, Any]:
    """Build the workspace/router packet payload."""

    packages = workspace_packages(report, facts, project_root, len(owner_nodes(facts)))
    edges = import_edges(facts, project_root, limit=MAX_WORKSPACE_EDGES)
    return {
        "header": header(
            "workspace",
            {
                "mode": "workspace-index",
                "package": project_name(facts),
                "packages": len(packages),
                "shown": len(packages),
                "edge": len(edges),
                "external": len(dependencies(facts)),
                "find": len(report.findings),
            },
        ),
        "packages": packages,
        "edges": edges,
        "findings": finding_facts(report, project_root),
        "nextActions": [
            {"kind": "prime", "target": item["id"]} for item in packages[:8]
        ],
    }


def prime_payload(
    report: PythonHarnessReport,
    facts: PythonReasoningTreeFacts,
    project_root: Path,
) -> dict[str, Any]:
    """Build the prime project map payload."""

    owners = ranked_owner_records(facts, project_root)[:MAX_PRIME_OWNERS]
    dep_nodes = [dependency_node(item) for item in dependencies(facts)]
    edges = import_edges(facts, project_root, limit=MAX_PRIME_EDGES)
    return {
        "header": header(
            "prime",
            {
                "mode": "prime-map",
                "package": project_name(facts),
                "owner": len(owner_nodes(facts)),
                "shown": len(owners),
                "edge": len(edges),
                "external": len(dep_nodes),
                "find": len(report.findings),
            },
        ),
        "nodes": dep_nodes[:MAX_DEPENDENCY_HITS],
        "owners": owners,
        "edges": edges,
        "findings": finding_facts(report, project_root),
        "nextActions": _prime_next_actions(owners, dep_nodes),
    }


def owner_payload(
    report: PythonHarnessReport,
    facts: PythonReasoningTreeFacts,
    project_root: Path,
    query: str,
) -> dict[str, Any]:
    """Build an owner slice payload."""

    matches = matching_owner_nodes(facts, project_root, query)
    owners = [owner_record(node, project_root) for node in matches[:MAX_PRIME_OWNERS]]
    owner_paths = {owner["path"] for owner in owners}
    edges = [
        edge
        for edge in import_edges(facts, project_root, limit=MAX_IMPORT_HITS)
        if edge["from"].removeprefix("O:") in owner_paths
        or edge["to"].removeprefix("O:") in owner_paths
    ]
    return {
        "header": header(
            "owner", {"q": query, "owner": len(owners), "edge": len(edges)}
        ),
        "owners": owners,
        "edges": edges,
        "hits": [
            path_hit(owner["path"], owner["path"], score=4, reason="owner-match")
            for owner in owners
        ],
        "findings": finding_facts(report, project_root, owner_paths=owner_paths),
        "nextActions": _owner_next_actions(owners),
        "notes": [] if owners else [{"kind": "owner-not-found", "message": query}],
    }


def _prime_next_actions(
    owners: list[dict[str, Any]],
    dep_nodes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for owner in owners[:3]:
        actions.append({"kind": "owner", "target": owner["path"]})
        if owner.get("exports"):
            actions.append(
                {
                    "kind": "text",
                    "target": owner["exports"][0],
                    "ownerPath": owner["path"],
                }
            )
    actions.extend(
        {"kind": "deps", "target": dependency}
        for dependency in _unique_dependencies(dep_nodes)
    )
    return actions[:8]


def _owner_next_actions(owners: list[dict[str, Any]]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for owner in owners[:8]:
        actions.append({"kind": "tests", "target": owner["path"]})
        actions.extend(
            {"kind": "text", "target": name, "ownerPath": owner["path"]}
            for name in owner.get("exports", [])[:2]
        )
    return actions


def _unique_dependencies(dep_nodes: list[dict[str, Any]]) -> list[str]:
    dependencies: list[str] = []
    seen: set[str] = set()
    for node in dep_nodes:
        dependency = node["id"].removeprefix("D:")
        if dependency in seen:
            continue
        seen.add(dependency)
        dependencies.append(dependency)
    return dependencies
