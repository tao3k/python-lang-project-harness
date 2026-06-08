"""Selector identity tests for Python tree-sitter-compatible queries."""

from __future__ import annotations

import io
from pathlib import Path

from semantic_search_fixture import write_search_fixture

from python_lang_project_harness import run_cli


def test_cli_query_exact_selector_scans_outside_default_report_sources(
    tmp_path: Path,
) -> None:
    (tmp_path / "dist").mkdir()
    (tmp_path / "dist" / "member.py").write_text(
        "def from_dist() -> str:\n    return 'dist'\n",
        encoding="utf-8",
    )
    stdout = io.StringIO()
    query = "(function_definition name: (identifier) @function.name)"

    exit_code = run_cli(
        _function_name_query_args(
            query,
            tmp_path,
            "--selector",
            "dist/member.py:1:2",
            "--code",
        ),
        stdout=stdout,
    )

    assert exit_code == 0
    assert stdout.getvalue() == "def from_dist() -> str:\n    return 'dist'\n"


def test_cli_query_selector_uses_canonical_paths_not_suffix_matching(
    tmp_path: Path,
) -> None:
    write_search_fixture(tmp_path)
    query = "(function_definition name: (identifier) @function.name)"

    suffix_stdout = io.StringIO()
    suffix_exit_code = run_cli(
        _function_name_query_args(
            query,
            tmp_path,
            "--selector",
            "service.py:9:10",
            "--code",
        ),
        stdout=suffix_stdout,
    )

    assert suffix_exit_code == 0
    assert suffix_stdout.getvalue() == ""

    absolute_stdout = io.StringIO()
    absolute_exit_code = run_cli(
        _function_name_query_args(
            query,
            tmp_path,
            "--selector",
            f"{tmp_path / 'src' / 'pkg' / 'service.py'}:9:10",
        ),
        stdout=absolute_stdout,
    )

    assert absolute_exit_code == 0
    assert "src/pkg/service.py:9\nfetch" in absolute_stdout.getvalue()


def _function_name_query_args(
    query: str,
    project_root: Path,
    *extra_args: str,
) -> list[str]:
    return [
        "query",
        "--treesitter-query",
        query,
        *extra_args,
        "--workspace",
        str(project_root),
        "--asp-syntax-query-captures",
        "function.name",
        "--asp-syntax-query-node-types",
        "function_definition,identifier",
        "--asp-syntax-query-fields",
        "name",
    ]
