"""Focused schema registration tests for the Python provider."""

from __future__ import annotations

from python_lang_project_harness import python_semantic_language_registration


def test_python_registration_advertises_semantic_fact_graph_schemas() -> None:
    registration = python_semantic_language_registration()
    schema_entries = {
        (schema["schemaId"], schema["path"]) for schema in registration["schemas"]
    }

    assert (
        "agent.semantic-protocols.semantic-fact-graph",
        "schemas/semantic-fact-graph.v1.schema.json",
    ) in schema_entries
    assert (
        "agent.semantic-protocols.semantic-fact-ontology",
        "schemas/semantic-fact-ontology.v1.schema.json",
    ) in schema_entries
