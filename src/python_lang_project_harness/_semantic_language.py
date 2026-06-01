"""Semantic-language registry metadata for the Python provider."""

from __future__ import annotations

from typing import Any

from ._semantic_language_catalog import python_search_view_descriptors

SEMANTIC_LANGUAGE_REGISTRY_ID = "agent.semantic-protocols.semantic-language-registry"
SEMANTIC_LANGUAGE_REGISTRY_VERSION = "1"
SEMANTIC_LANGUAGE_PROTOCOL_ID = "agent.semantic-protocols.semantic-language"
SEMANTIC_LANGUAGE_PROTOCOL_VERSION = "1"
SEMANTIC_SEARCH_PACKET_SCHEMA_ID = "agent.semantic-protocols.semantic-search-packet"
PYTHON_CAPABILITIES_SCHEMA_ID = (
    "agent.semantic-protocols.languages.python.py-harness.capabilities"
)
PYTHON_LANGUAGE_ID = "python"
PYTHON_PROVIDER_ID = "py-harness"
PYTHON_BINARY = "py-harness"
PYTHON_PROVIDER_NAMESPACE = "agent.semantic-protocols.languages.python.py-harness"

PYTHON_CHECK_METHODS = ("check/changed", "check/full")
PYTHON_AGENT_METHODS = ("agent/doctor",)
PYTHON_SEARCH_VIEW_DESCRIPTORS = python_search_view_descriptors()
PYTHON_SEARCH_VIEWS = tuple(
    descriptor["view"] for descriptor in PYTHON_SEARCH_VIEW_DESCRIPTORS
)
PYTHON_SEARCH_METHODS = tuple(f"search/{view}" for view in PYTHON_SEARCH_VIEWS)


def semantic_language_registry_document(
    project_root: str | None = None,
) -> dict[str, Any]:
    """Return the provider registry document advertised by agent doctor."""

    payload: dict[str, Any] = {
        "registryId": SEMANTIC_LANGUAGE_REGISTRY_ID,
        "registryVersion": SEMANTIC_LANGUAGE_REGISTRY_VERSION,
        "protocolId": SEMANTIC_LANGUAGE_PROTOCOL_ID,
        "protocolVersion": SEMANTIC_LANGUAGE_PROTOCOL_VERSION,
        "languages": [python_semantic_language_registration()],
    }
    if project_root is not None:
        payload["projectRoot"] = project_root
    return payload


def python_semantic_language_registration() -> dict[str, Any]:
    """Return the Python semantic-language provider registration."""

    return {
        "languageId": PYTHON_LANGUAGE_ID,
        "providerId": PYTHON_PROVIDER_ID,
        "binary": PYTHON_BINARY,
        "namespace": PYTHON_PROVIDER_NAMESPACE,
        "displayName": "Python",
        "methods": [
            *PYTHON_SEARCH_METHODS,
            *PYTHON_CHECK_METHODS,
            *PYTHON_AGENT_METHODS,
        ],
        "methodDescriptors": python_semantic_language_method_descriptors(),
        "schemas": [
            {
                "schemaId": SEMANTIC_SEARCH_PACKET_SCHEMA_ID,
                "schemaVersion": "1",
                "path": "schemas/semantic-search-packet.v1.schema.json",
            },
            {
                "schemaId": SEMANTIC_LANGUAGE_REGISTRY_ID,
                "schemaVersion": SEMANTIC_LANGUAGE_REGISTRY_VERSION,
                "path": "schemas/semantic-language-registry.v1.schema.json",
            },
            {
                "schemaId": PYTHON_CAPABILITIES_SCHEMA_ID,
                "schemaVersion": "1",
                "path": "schemas/python-semantic-capabilities.v1.schema.json",
            },
        ],
    }


def python_semantic_language_method_descriptors() -> list[dict[str, Any]]:
    """Return method descriptors for the Python provider registry."""

    descriptors = [
        {
            **descriptor,
            "outputSchemaIds": [SEMANTIC_SEARCH_PACKET_SCHEMA_ID],
            "supportsJson": True,
            "supportsCompact": True,
        }
        for descriptor in PYTHON_SEARCH_VIEW_DESCRIPTORS
    ]
    descriptors.extend(
        {
            "method": method,
            "command": "check",
            "supportsJson": True,
            "supportsCompact": True,
        }
        for method in PYTHON_CHECK_METHODS
    )
    descriptors.append(
        {
            "method": "agent/doctor",
            "command": "agent",
            "outputSchemaIds": [SEMANTIC_LANGUAGE_REGISTRY_ID],
            "supportsJson": True,
            "supportsCompact": True,
        }
    )
    return descriptors


def python_semantic_search_view_descriptor(view: str) -> dict[str, Any] | None:
    """Return the registry descriptor for one search view."""

    return next(
        (
            descriptor
            for descriptor in PYTHON_SEARCH_VIEW_DESCRIPTORS
            if descriptor["view"] == view
        ),
        None,
    )


def is_python_semantic_search_view(view: str) -> bool:
    """Return whether a view is implemented by the Python provider."""

    return python_semantic_search_view_descriptor(view) is not None
