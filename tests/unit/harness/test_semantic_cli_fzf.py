"""Semantic CLI fzf protocol tests."""

from __future__ import annotations

import io
from pathlib import Path

from python_lang_project_harness._cli import run_cli

from semantic_search_fixture import write_search_fixture


def test_cli_search_fzf_query_set(tmp_path: Path) -> None:
    write_search_fixture(tmp_path)
    stdout = io.StringIO()
    exit_code = run_cli(
        [
            "search",
            "fzf",
            "--query-set",
            "build",
            "--query-set",
            "Session",
            "owner",
            "tests",
            "--owner",
            "src/pkg/service.py",
            str(tmp_path),
        ],
        stdout=stdout,
    )
    rendered = stdout.getvalue()
    assert exit_code == 0
    assert rendered.startswith('[search-fzf] q="build,Session" querySet=2')
    assert "selector=fuzzy-set" in rendered
    assert "scopeOwner=src/pkg/service.py" in rendered
    assert "|seed owner:src/pkg/service.py,tests:src/pkg/service.py" in rendered


def test_cli_search_fzf_matches_path_only_candidate(tmp_path: Path) -> None:
    write_search_fixture(tmp_path)
    path_owner = tmp_path / "src" / "pkg" / "hook_runtime.py"
    path_owner.write_text(
        '"""Path-only fuzzy owner."""\n\n'
        "def execute() -> None:\n"
        "    pass\n",
        encoding="utf-8",
    )
    stdout = io.StringIO()
    exit_code = run_cli(
        ["search", "fzf", "hookruntime", "owner", "tests", "--view", "seeds", str(tmp_path)],
        stdout=stdout,
    )
    rendered = stdout.getvalue()
    assert exit_code == 0
    assert rendered.startswith("[search-fzf] q=hookruntime")
    assert "|seed owner:src/pkg/hook_runtime.py" in rendered
