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
        _function_name_query_args(query, tmp_path),
        stdout=stdout,
    )

    rendered = stdout.getvalue()
    assert exit_code == 0
    assert "src/pkg/service.py:9\nfetch" in rendered
    assert "|syntax-capture" not in rendered
    assert "pub fn" not in rendered
    assert "|syntax-query inputForm" not in rendered


def test_cli_query_inline_s_expression_requires_asp_compiled_plan(
    tmp_path: Path,
) -> None:
    write_search_fixture(tmp_path)
    stdout = io.StringIO()
    query = "(function_definition name: (identifier) @function.name)"

    exit_code = run_cli(
        ["query", "--treesitter-query", query, str(tmp_path)],
        stdout=stdout,
    )

    assert exit_code != 0


def test_cli_query_catalog_code_flag_returns_pure_python_code(
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
    assert stdout.getvalue() == (
        "def build(value: str) -> str:\n    return value.strip()\n"
    )


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
    assert packet["matches"][0]["captures"][0]["nodeType"] == "identifier"
    assert packet["matches"][0]["captures"][0]["field"] == "name"
    assert (
        packet["matches"][0]["captures"][0]["fields"]["nativeNodeType"]
        == "class_definition"
    )
    assert packet["nativeFactRefs"][0].startswith("python:ast:src/pkg/service.py:")


def test_cli_query_inline_call_target_uses_target_capture_node_and_field(
    tmp_path: Path,
) -> None:
    (tmp_path / "sample.py").write_text(
        "def parse_query():\n    return 1\n\ndef run():\n    parse_query()\n",
        encoding="utf-8",
    )
    stdout = io.StringIO()
    query = "(call function: (identifier) @call.target)"

    exit_code = run_cli(
        [
            "query",
            "--treesitter-query",
            query,
            "--json",
            str(tmp_path),
            "--asp-syntax-query-captures",
            "call.target",
            "--asp-syntax-query-node-types",
            "call,identifier",
            "--asp-syntax-query-fields",
            "function",
        ],
        stdout=stdout,
    )

    assert exit_code == 0
    packet = json.loads(stdout.getvalue())
    capture = packet["matches"][0]["captures"][0]
    assert capture["name"] == "call.target"
    assert capture["nodeType"] == "identifier"
    assert capture["field"] == "function"
    assert capture["fields"]["nativeNodeType"] == "call"
    assert capture["fields"]["read"] == "sample.py:5"
    assert capture["fields"]["itemRead"] == "sample.py:5"


def test_cli_owner_item_query_packet_links_python_syntax_refs(
    tmp_path: Path,
) -> None:
    write_search_fixture(tmp_path)
    stdout = io.StringIO()

    exit_code = run_cli(
        ["query", "src/pkg/service.py", "--term", "build", "--json", str(tmp_path)],
        stdout=stdout,
    )

    assert exit_code == 0
    packet = json.loads(stdout.getvalue())
    assert packet["syntaxQueryRef"] == (
        "semantic-tree-sitter-query/python-owner-items.v1"
    )
    assert packet["syntaxMatchRefs"] == ["match.1"]
    assert packet["syntaxCaptureRefs"] == ["capture.1"]
    assert packet["matches"][0]["fields"]["syntaxQueryRef"] == (
        "semantic-tree-sitter-query/python-owner-items.v1"
    )
    assert packet["matches"][0]["fields"]["syntaxMatchRef"] == "match.1"
    assert packet["matches"][0]["fields"]["syntaxCaptureRef"] == "capture.1"


def test_cli_search_owner_items_packet_links_python_syntax_refs(
    tmp_path: Path,
) -> None:
    write_search_fixture(tmp_path)
    stdout = io.StringIO()

    exit_code = run_cli(
        [
            "search",
            "owner",
            "src/pkg/service.py",
            "items",
            "--query",
            "build",
            "--json",
            str(tmp_path),
        ],
        stdout=stdout,
    )

    assert exit_code == 0
    packet = json.loads(stdout.getvalue())
    assert packet["syntaxQueryRef"] == (
        "semantic-tree-sitter-query/python-owner-items.v1"
    )
    assert packet["syntaxMatchRefs"] == ["match.1"]
    assert packet["syntaxCaptureRefs"] == ["capture.1"]
    assert packet["items"][0]["fields"]["syntaxQueryRef"] == (
        "semantic-tree-sitter-query/python-owner-items.v1"
    )


def _function_name_query_args(
    query: str,
    project_root: Path,
    plan_args: list[str] | None = None,
    *extra_args: str,
) -> list[str]:
    return [
        "query",
        "--treesitter-query",
        query,
        *extra_args,
        str(project_root),
        "--asp-syntax-query-captures",
        "function.name",
        "--asp-syntax-query-node-types",
        "function_definition,identifier",
        "--asp-syntax-query-fields",
        "name",
        *(plan_args or []),
    ]
