"""Semantic search ingest CLI parsing tests."""

from __future__ import annotations

from pathlib import Path

from python_lang_project_harness import python_semantic_language_registration
from python_lang_project_harness._semantic_search_cli import parse_semantic_search_args


def test_search_ingest_descriptor_accepts_items_tests_pipes() -> None:
    descriptors = python_semantic_language_registration()["methodDescriptors"]

    assert any(
        descriptor["method"] == "search/ingest"
        and descriptor["acceptedPipes"] == ["items", "tests"]
        and descriptor["acceptsStdin"] is True
        for descriptor in descriptors
    )


def test_search_ingest_accepts_pipes_before_project_root() -> None:
    parsed = parse_semantic_search_args(
        ["ingest", "items", "tests", "--view", "seeds", "."]
    )

    assert parsed.error is None
    assert parsed.view == "ingest"
    assert parsed.pipes == ("items", "tests")
    assert parsed.project_root == Path(".")
    assert parsed.render_mode == "seeds"


def test_search_ingest_rejects_extra_positional_root_after_pipes() -> None:
    parsed = parse_semantic_search_args(
        ["ingest", "items", "tests", "extra", "--view", "seeds", "."]
    )

    assert parsed.error == "expected at most one PROJECT_ROOT argument"
