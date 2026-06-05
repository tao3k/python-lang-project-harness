"""Tree-sitter-compatible syntax query tests for the Python semantic CLI."""

from __future__ import annotations

import io
import json
from pathlib import Path

from semantic_search_fixture import write_search_fixture

from python_lang_project_harness import run_cli


def test_cli_query_catalog_packet_uses_provider_embedded_sources(
    tmp_path: Path,
) -> None:
    stdout = io.StringIO()

    exit_code = run_cli(
        ["query", "--catalog", "calls", "--json", str(tmp_path)],
        stdout=stdout,
    )

    assert exit_code == 0
    packet = json.loads(stdout.getvalue())
    assert packet["schemaId"] == "agent.semantic-protocols.semantic-tree-sitter-query"
    assert packet["grammarId"] == "tree-sitter-python"
    assert packet["query"]["catalogId"] == "calls"
    assert packet["query"]["catalogPath"] == (
        "tree-sitter/tree-sitter-python/queries/calls.scm"
    )
    assert packet["query"]["grammarProfilePath"] == (
        "tree-sitter/tree-sitter-python/grammar-profile.json"
    )
    assert "call.target" in packet["query"]["fields"]["captures"]
    assert packet["cache"]["artifactKind"] == "semantic-tree-sitter-query"


def test_cli_query_inline_s_expression_projects_python_functions(
    tmp_path: Path,
) -> None:
    write_search_fixture(tmp_path)
    stdout = io.StringIO()
    query = "(function_definition name: (identifier) @function.name)"

    exit_code = run_cli(
        ["query", "--treesitter-query", query, str(tmp_path)],
        stdout=stdout,
    )

    rendered = stdout.getvalue()
    assert exit_code == 0
    assert (
        "|syntax-capture capture=function.name node=function_definition "
        "name=fetch captureAt=src/pkg/service.py:9:10 "
        "read=src/pkg/service.py:9:10 frontier=code"
    ) in rendered
    assert "pub fn" not in rendered
    assert "|syntax-query inputForm" not in rendered


def test_cli_query_catalog_code_flag_returns_compact_python_code(
    tmp_path: Path,
) -> None:
    write_search_fixture(tmp_path)
    stdout = io.StringIO()

    exit_code = run_cli(
        [
            "query",
            "--catalog",
            "declarations",
            "--term",
            "build",
            "--selector",
            "src/pkg/service.py",
            "--code",
            str(tmp_path),
        ],
        stdout=stdout,
    )

    assert exit_code == 0
    assert stdout.getvalue() == "def build(value: str) -> str:\n  return strip\n"


def test_cli_query_catalog_json_projects_native_capture_rows(
    tmp_path: Path,
) -> None:
    write_search_fixture(tmp_path)
    stdout = io.StringIO()

    exit_code = run_cli(
        [
            "query",
            "--catalog",
            "declarations",
            "--term",
            "SessionClient",
            "--json",
            str(tmp_path),
        ],
        stdout=stdout,
    )

    assert exit_code == 0
    packet = json.loads(stdout.getvalue())
    assert packet["matches"][0]["captures"][0]["name"] == "class.name"
    assert packet["matches"][0]["captures"][0]["nodeType"] == "class_definition"
    assert packet["nativeFactRefs"][0].startswith("python:ast:src/pkg/service.py:")
