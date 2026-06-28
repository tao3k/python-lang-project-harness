"""Compact graph query-route tests for the Python semantic CLI."""

from __future__ import annotations

import io
from pathlib import Path

from semantic_search_fixture import write_search_fixture

from python_lang_project_harness import run_cli


def test_cli_query_hook_wildcard_seeds_use_shared_compact_graph(
    tmp_path: Path,
) -> None:
    write_search_fixture(tmp_path)
    stdout = io.StringIO()
    stderr = io.StringIO()

    exit_code = run_cli(
        [
            "query",
            "--from-hook",
            "owner-local-projection",
            "--selector",
            "**/*.py",
            "--term",
            "build",
            "--surface",
            "owners,tests",
            "--view",
            "seeds",
            "--workspace",
            str(tmp_path),
        ],
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 2
    assert stdout.getvalue() == ""
    assert "query --surface is Rust ASP search-owned" in stderr.getvalue()
