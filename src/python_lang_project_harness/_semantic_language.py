"""Semantic-language registry metadata for the Python provider."""

from __future__ import annotations

from typing import Any

from . import _semantic_language_ids as ids
from ._semantic_language_catalog import python_search_view_descriptors

_PYTHON_CHECK_METHODS = ("check/changed", "check/full")
_PYTHON_QUERY_METHODS = ("query/owner-items", "query/direct-source-read")
_PYTHON_AGENT_METHODS = ("agent/doctor", "agent/guide")
_PYTHON_SEARCH_VIEW_DESCRIPTORS = python_search_view_descriptors()
_PYTHON_SEARCH_VIEWS = tuple(
    descriptor["view"] for descriptor in _PYTHON_SEARCH_VIEW_DESCRIPTORS
)
_PYTHON_SEARCH_METHODS = tuple(f"search/{view}" for view in _PYTHON_SEARCH_VIEWS)


def semantic_language_registry_document(
    project_root: str | None = None,
) -> dict[str, Any]:
    """Return the provider registry document advertised by agent doctor."""

    payload: dict[str, Any] = {
        "registryId": ids.SEMANTIC_LANGUAGE_REGISTRY_ID,
        "registryVersion": ids.SEMANTIC_LANGUAGE_REGISTRY_VERSION,
        "protocolId": ids.SEMANTIC_LANGUAGE_PROTOCOL_ID,
        "protocolVersion": ids.SEMANTIC_LANGUAGE_PROTOCOL_VERSION,
        "languages": [python_semantic_language_registration()],
    }
    if project_root is not None:
        payload["projectRoot"] = project_root
    return payload


def python_semantic_language_registration() -> dict[str, Any]:
    """Return the Python semantic-language provider registration."""

    return {
        "languageId": ids.PYTHON_LANGUAGE_ID,
        "providerId": ids.PYTHON_PROVIDER_ID,
        "binary": ids.PYTHON_BINARY,
        "namespace": ids.PYTHON_PROVIDER_NAMESPACE,
        "displayName": "Python",
        "methods": [
            *_PYTHON_SEARCH_METHODS,
            *_PYTHON_QUERY_METHODS,
            *_PYTHON_CHECK_METHODS,
            *_PYTHON_AGENT_METHODS,
        ],
        "methodDescriptors": python_semantic_language_method_descriptors(),
        "schemas": _python_semantic_language_schemas(),
    }


def _python_semantic_language_schemas() -> list[dict[str, str]]:
    return [
        {
            "schemaId": ids.SEMANTIC_SEARCH_PACKET_SCHEMA_ID,
            "schemaVersion": "1",
            "path": "schemas/semantic-search-packet.v1.schema.json",
        },
        {
            "schemaId": ids.SEMANTIC_QUERY_PACKET_SCHEMA_ID,
            "schemaVersion": "1",
            "path": "schemas/semantic-query-packet.v1.schema.json",
        },
        {
            "schemaId": ids.SEMANTIC_READ_PACKET_SCHEMA_ID,
            "schemaVersion": "1",
            "path": "schemas/semantic-read-packet.v1.schema.json",
        },
        {
            "schemaId": ids.SEMANTIC_GRAPH_SCHEMA_ID,
            "schemaVersion": "1",
            "path": "schemas/semantic-graph.v1.schema.json",
        },
        {
            "schemaId": "agent.semantic-protocols.semantic-verification-receipt",
            "schemaVersion": "1",
            "path": "schemas/semantic-verification-receipt.v1.schema.json",
        },
        {
            "schemaId": "agent.semantic-protocols.semantic-behavior-snapshot",
            "schemaVersion": "1",
            "path": "schemas/semantic-behavior-snapshot.v1.schema.json",
        },
        {
            "schemaId": ids.SEMANTIC_DETERMINISM_READINESS_SCHEMA_ID,
            "schemaVersion": "1",
            "path": "schemas/semantic-determinism-readiness.v1.schema.json",
        },
        {
            "schemaId": ids.SEMANTIC_DEV_COMMAND_LOG_SCHEMA_ID,
            "schemaVersion": "1",
            "path": "schemas/semantic-dev-command-log.v1.schema.json",
        },
        {
            "schemaId": ids.SEMANTIC_FORMAL_PROOF_PILOT_SCHEMA_ID,
            "schemaVersion": "1",
            "path": "schemas/semantic-formal-proof-pilot.v1.schema.json",
        },
        {
            "schemaId": ids.SEMANTIC_REVIEW_PACKET_SCHEMA_ID,
            "schemaVersion": "1",
            "path": "schemas/semantic-review-packet.v1.schema.json",
        },
        {
            "schemaId": ids.SEMANTIC_EVIDENCE_GRAPH_SCHEMA_ID,
            "schemaVersion": "1",
            "path": "schemas/semantic-evidence-graph.v1.schema.json",
        },
        {
            "schemaId": ids.SEMANTIC_ASSURANCE_CASE_SCHEMA_ID,
            "schemaVersion": "1",
            "path": "schemas/semantic-assurance-case.v1.schema.json",
        },
        {
            "schemaId": ids.SEMANTIC_TYPE_SURFACE_SCHEMA_ID,
            "schemaVersion": "1",
            "path": "schemas/semantic-type-surface.v1.schema.json",
        },
        {
            "schemaId": "agent.semantic-protocols.semantic-handle",
            "schemaVersion": "1",
            "path": "schemas/semantic-handle.v1.schema.json",
        },
        {
            "schemaId": ids.SEMANTIC_LANGUAGE_REGISTRY_ID,
            "schemaVersion": ids.SEMANTIC_LANGUAGE_REGISTRY_VERSION,
            "path": "schemas/semantic-language-registry.v1.schema.json",
        },
        {
            "schemaId": ids.PYTHON_CAPABILITIES_SCHEMA_ID,
            "schemaVersion": "1",
            "path": "schemas/python-semantic-capabilities.v1.schema.json",
        },
    ]


def python_semantic_language_method_descriptors() -> list[dict[str, Any]]:
    """Return method descriptors for the Python provider registry."""

    descriptors = [
        {
            **descriptor,
            "outputSchemaIds": _search_output_schema_ids(descriptor["view"]),
            "supportsJson": True,
            "supportsCompact": True,
        }
        for descriptor in _PYTHON_SEARCH_VIEW_DESCRIPTORS
    ]
    descriptors.extend(
        [
            {
                "method": "query/owner-items",
                "command": "query",
                "input": "owner-path",
                "requiredOptions": ["--term"],
                "outputSchemaIds": [ids.SEMANTIC_QUERY_PACKET_SCHEMA_ID],
                "supportsJson": True,
                "supportsCompact": True,
                "supportsQuerySet": True,
                "acceptedQuerySetSelectors": ["exact-set"],
                "querySetScopes": ["owner"],
                "outputModes": ["compact", "json", "code", "names"],
            },
            {
                "method": "query/direct-source-read",
                "command": "query",
                "input": "owner-path",
                "requiredOptions": ["--from-hook", "--selector"],
                "outputSchemaIds": [ids.SEMANTIC_QUERY_PACKET_SCHEMA_ID],
                "supportsJson": True,
                "supportsCompact": True,
                "outputModes": ["compact", "json", "names"],
            },
        ]
    )
    descriptors.extend(
        {
            "method": method,
            "command": "check",
            "supportsJson": True,
            "supportsCompact": True,
        }
        for method in _PYTHON_CHECK_METHODS
    )
    descriptors.extend(
        [
            {
                "method": "agent/doctor",
                "command": "agent",
                "outputSchemaIds": [ids.SEMANTIC_LANGUAGE_REGISTRY_ID],
                "supportsJson": True,
                "supportsCompact": True,
            },
            {
                "method": "agent/guide",
                "command": "agent",
                "supportsJson": False,
                "supportsCompact": True,
            },
        ]
    )
    return descriptors


def _search_output_schema_ids(view: str) -> list[str]:
    schema_ids = [ids.SEMANTIC_SEARCH_PACKET_SCHEMA_ID]
    if view == "public-external-types":
        schema_ids.append(ids.SEMANTIC_TYPE_SURFACE_SCHEMA_ID)
    if view == "policy":
        schema_ids.append("agent.semantic-protocols.semantic-handle")
    return schema_ids


def python_semantic_search_view_descriptor(view: str) -> dict[str, Any] | None:
    """Return the registry descriptor for one search view."""

    return next(
        (
            descriptor
            for descriptor in _PYTHON_SEARCH_VIEW_DESCRIPTORS
            if descriptor["view"] == view
        ),
        None,
    )


def is_python_semantic_search_view(view: str) -> bool:
    """Return whether a view is implemented by the Python provider."""

    return python_semantic_search_view_descriptor(view) is not None
