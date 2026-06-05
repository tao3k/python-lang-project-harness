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

    exit_code = run_cli(
        [
            "query",
            "--from-hook",
            "direct-source-read",
            "--selector",
            "**/*.py",
            "--term",
            "build",
            "--surface",
            "owners,tests",
            "--view",
            "seeds",
            str(tmp_path),
        ],
        stdout=stdout,
    )

    rendered = stdout.getvalue()
    assert exit_code == 0
    assert rendered.startswith("[search-fzf] q=build")
    assert (
        "legend: ID=kind:role(value)!next; edge SRC>{DST:rel}; frontier ID.next"
    ) in rendered
    assert "aliases: graph:{G=search,Q=query,O=owner,T=test}" in rendered
    assert "Q=query:term(build)!fzf" in rendered
    assert "src/pkg/service.py" in rendered
    assert "G>{Q:matches," in rendered
    assert "frontier=Q.fzf," in rendered
    assert "|seed " not in rendered
    assert "alias: graph:" not in rendered
