"""Top-level semantic-search packet assembly for the Python provider."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ._semantic_language import (
    PYTHON_BINARY,
    PYTHON_LANGUAGE_ID,
    PYTHON_PROVIDER_ID,
    PYTHON_PROVIDER_NAMESPACE,
    SEMANTIC_LANGUAGE_PROTOCOL_ID,
    SEMANTIC_LANGUAGE_PROTOCOL_VERSION,
    SEMANTIC_SEARCH_PACKET_SCHEMA_ID,
)
from ._semantic_search_model import PythonSemanticSearchOptions
from ._semantic_search_views import payload_for_view
from .verification.facts import (
    verification_project_root,
    verification_reasoning_tree_facts,
)

if TYPE_CHECKING:
    from ._model import PythonHarnessReport


def build_python_semantic_search_packet(
    report: PythonHarnessReport,
    options: PythonSemanticSearchOptions,
) -> dict[str, Any]:
    """Build a language-neutral semantic-search packet from Python parser facts."""

    facts = verification_reasoning_tree_facts(report)
    project_root = verification_project_root(report)
    payload = payload_for_view(report, facts, project_root, options)
    packet: dict[str, Any] = {
        "schemaId": SEMANTIC_SEARCH_PACKET_SCHEMA_ID,
        "schemaVersion": "1",
        "protocolId": SEMANTIC_LANGUAGE_PROTOCOL_ID,
        "protocolVersion": SEMANTIC_LANGUAGE_PROTOCOL_VERSION,
        "languageId": PYTHON_LANGUAGE_ID,
        "providerId": PYTHON_PROVIDER_ID,
        "binary": PYTHON_BINARY,
        "namespace": PYTHON_PROVIDER_NAMESPACE,
        "method": f"search/{options.view}",
        "projectRoot": str(project_root),
        "view": options.view,
        "renderMode": options.render_mode or "both",
        "header": payload["header"],
        "nodes": payload.get("nodes", []),
        "edges": payload.get("edges", []),
        "owners": payload.get("owners", []),
        "hits": payload.get("hits", []),
        "findings": payload.get("findings", []),
        "nextActions": payload.get("nextActions", []),
        "notes": payload.get("notes", []),
    }
    if options.query is not None:
        packet["query"] = options.query
    query_terms = [
        {"value": term, "kind": "text", "selector": "exact"}
        for term in _normalized_query_set(options.query_set)
    ]
    if query_terms:
        packet["querySet"] = query_terms
        scope = (
            {"ownerPath": options.owner_path}
            if options.owner_path is not None
            else None
        )
        packet["queryComposition"] = {
            "mode": "query-set",
            "view": options.view,
            "selector": "exact-set",
            **({} if scope is None else {"scope": scope}),
            "merge": ["nodes", "edges", "owners", "hits", "nextActions", "notes"],
        }
    if facts.project_metadata is not None and facts.project_metadata.project_name:
        packet["packageName"] = facts.project_metadata.project_name
    if options.runtime_cost is not None:
        packet["runtimeCost"] = options.runtime_cost
        packet["notes"] = [
            *packet["notes"],
            {
                "kind": "runtime-prefilter",
                "message": str(options.runtime_cost.get("reason", "")),
                "fields": options.runtime_cost.get("fields", {}),
            },
        ]
    for optional_key in (
        "inputDetection",
        "packages",
        "items",
        "queryCoverage",
        "ownerResolution",
        "runtimeCost",
        "searchSynthesis",
        "avoidNextActions",
    ):
        if payload.get(optional_key) is not None:
            packet[optional_key] = payload[optional_key]
    return packet


def _normalized_query_set(query_set: tuple[str, ...]) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()
    for raw_term in query_set:
        term = raw_term.strip()
        if not term or term in seen:
            continue
        seen.add(term)
        terms.append(term)
    return terms
