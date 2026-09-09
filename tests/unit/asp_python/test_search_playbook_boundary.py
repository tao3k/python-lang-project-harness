from __future__ import annotations

import pytest

from asp_python import python_semantic_language_registration
from asp_python._cli_args import ProtocolArgs


@pytest.mark.parametrize("operation", ["prime", "owner", "lexical", "ingest", "pipe"])
def test_provider_local_search_operations_are_hard_cut(operation: str) -> None:
    parsed = ProtocolArgs.parse(["search", operation, "fixture"])

    assert parsed is not None
    assert parsed.command == "error"
    assert parsed.error == (
        "provider-local search was removed; use asp python search playbook <query>"
    )


def test_public_playbook_is_owned_by_the_asp_client() -> None:
    parsed = ProtocolArgs.parse(["search", "playbook", "native syntax"])

    assert parsed is not None
    assert parsed.command == "error"
    assert parsed.error == (
        "provider-local search was removed; use asp python search playbook <query>"
    )


def test_provider_registry_exposes_no_search_orchestration_method() -> None:
    registration = python_semantic_language_registration()
    assert [
        method for method in registration["methods"] if method.startswith("search/")
    ] == []
    descriptors = [
        descriptor
        for descriptor in registration["methodDescriptors"]
        if descriptor["method"].startswith("search/")
    ]
    assert descriptors == []
