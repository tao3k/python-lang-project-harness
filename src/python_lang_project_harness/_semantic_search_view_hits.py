"""Hit-oriented semantic-search views for Python."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from ._semantic_search_common import dedupe, header, path_hit
from ._semantic_search_hits import test_path_hits, text_hits
from ._semantic_search_ingest import ingest_hits
from ._semantic_search_model import (
    MAX_TEST_HITS,
    MAX_TEXT_HITS,
)
from ._semantic_search_owners import (
    matching_owner_nodes,
    owner_record,
    owners_for_paths,
    test_edges,
)

if TYPE_CHECKING:
    from python_lang_parser import PythonReasoningTreeFacts

    from ._model import PythonHarnessReport


def tests_payload(
    report: PythonHarnessReport,
    facts: PythonReasoningTreeFacts,
    project_root: Path,
    query: str,
) -> dict[str, Any]:
    """Build tests-for-owner payloads."""

    owner_paths = {
        owner_record(node, project_root)["path"]
        for node in matching_owner_nodes(facts, project_root, query)
    }
    edges = test_edges(facts, project_root, owner_paths)
    hits = [
        path_hit(
            edge["to"].removeprefix("O:"),
            edge["to"].removeprefix("O:"),
            kind="test",
            score=4,
            reason="test-import",
        )
        for edge in edges
    ]
    if not hits and not owner_paths:
        hits = test_path_hits(report, project_root, query)
    return generic_hits_payload(
        "tests",
        hits[:MAX_TEST_HITS],
        facts,
        project_root,
        query,
        edges=edges[:MAX_TEST_HITS],
    )


def text_payload(
    report: PythonHarnessReport,
    facts: PythonReasoningTreeFacts,
    project_root: Path,
    query: str,
    pipes: tuple[str, ...],
) -> dict[str, Any]:
    """Build parser-visible text search payloads."""

    hits = text_hits(report, facts, project_root, query)[:MAX_TEXT_HITS]
    owner_paths = dedupe(hit["ownerPath"] for hit in hits)
    owners = (
        owners_for_paths(facts, project_root, owner_paths) if "owner" in pipes else []
    )
    edges = (
        test_edges(facts, project_root, set(owner_paths)) if "tests" in pipes else []
    )
    return {
        "header": header(
            "text",
            {
                "q": query,
                "own": len(owner_paths),
                "hit": len(hits),
                "view": "hits",
                "pipes": list(pipes),
            },
        ),
        "owners": owners,
        "edges": edges[:MAX_TEST_HITS],
        "hits": hits,
        "nextActions": hit_next_actions(hits),
        "notes": [] if hits else [{"kind": "not-found", "message": query}],
    }


def ingest_payload(
    facts: PythonReasoningTreeFacts,
    project_root: Path,
    stdin: str,
) -> dict[str, Any]:
    """Build stdin ingest payloads."""

    detection, hits = ingest_hits(facts, project_root, stdin)
    hits = hits[:MAX_TEXT_HITS]
    return {
        "header": header(
            "ingest",
            {
                "source": detection["source"],
                "hit": len(hits),
                "bytes": detection["byteCount"],
            },
        ),
        "inputDetection": detection,
        "owners": owners_for_paths(
            facts, project_root, [hit["ownerPath"] for hit in hits]
        ),
        "hits": hits,
        "nextActions": hit_next_actions(hits),
        "notes": []
        if hits
        else [{"kind": "unrecognized-input", "message": "stdin produced no path hits"}],
    }


def generic_hits_payload(
    view: str,
    hits: list[dict[str, Any]],
    facts: PythonReasoningTreeFacts,
    project_root: Path,
    query: str,
    *,
    edges: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a generic hit-oriented payload."""

    return {
        "header": header(view, {"q": query, "hit": len(hits)}),
        "owners": owners_for_paths(
            facts, project_root, [hit["ownerPath"] for hit in hits]
        ),
        "edges": edges or [],
        "hits": hits,
        "nextActions": hit_next_actions(hits),
        "notes": [] if hits else [{"kind": "not-found", "message": query}],
    }


def hit_next_actions(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return bounded owner/tests follow-up actions for hits."""

    actions: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for hit in hits:
        for action in (
            {"kind": "owner", "target": hit["ownerPath"]},
            {"kind": "tests", "target": hit["ownerPath"]},
        ):
            key = (action["kind"], action["target"])
            if key in seen:
                continue
            seen.add(key)
            actions.append(action)
            if len(actions) >= 8:
                return actions
    return actions
