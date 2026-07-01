"""Semantic CLI fzf protocol tests."""

from __future__ import annotations

import io
from pathlib import Path

from semantic_search_fixture import require_compact_graph_renderer, write_search_fixture

from python_lang_project_harness._cli import run_cli


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
            "--workspace",
            str(tmp_path),
        ],
        stdout=stdout,
    )
    rendered = stdout.getvalue()
    assert exit_code == 0
    assert rendered.startswith('[search-fzf] q="build,Session" querySet=2')
    assert "selector=fuzzy-set" in rendered
    assert "scopeOwner=src/pkg/service.py" in rendered
    assert "|seed owner:src/pkg/service.py" in rendered
    assert "|next owner:src/pkg/service.py,tests:src/pkg/service.py" in rendered
    for line in rendered.splitlines():
        if line.startswith("|seed "):
            assert ",owner:" not in line
            assert ",tests:" not in line


def test_cli_search_fzf_matches_path_only_candidate(tmp_path: Path) -> None:
    require_compact_graph_renderer()
    write_search_fixture(tmp_path)
    path_owner = tmp_path / "src" / "pkg" / "hook_runtime.py"
    path_owner.write_text(
        '"""Path-only fuzzy owner."""\n\ndef execute() -> None:\n    pass\n',
        encoding="utf-8",
    )
    stdout = io.StringIO()
    exit_code = run_cli(
        [
            "search",
            "fzf",
            "hookruntime",
            "owner",
            "tests",
            "--view",
            "seeds",
            "--workspace",
            str(tmp_path),
        ],
        stdout=stdout,
    )
    rendered = stdout.getvalue()
    assert exit_code == 0
    assert rendered.startswith("[search-fzf] q=hookruntime")
    assert "O=owner:path(src/pkg/hook_runtime.py)!owner" in rendered
    assert "rank=Q,O,T frontier=Q.fzf,O.owner,T.tests" in rendered
    assert "|seed " not in rendered


def test_protocol_search_fzf_positional_query_uses_fast_frontier(
    tmp_path: Path,
) -> None:
    from python_lang_project_harness._cli_args import ProtocolArgs
    from python_lang_project_harness._cli_protocol import run_protocol_cli

    write_search_fixture(tmp_path)
    path_owner = tmp_path / "src" / "pkg" / "hook_runtime.py"
    path_owner.write_text(
        '"""Path-only fuzzy owner."""\n\ndef execute() -> None:\n    pass\n',
        encoding="utf-8",
    )
    args = ProtocolArgs.parse(
        [
            "search",
            "fzf",
            "hookruntime",
            "owner",
            "tests",
            "--view",
            "seeds",
            "--workspace",
            str(tmp_path),
        ]
    )
    stdout = io.StringIO()
    stderr = io.StringIO()
    assert args is not None
    exit_code = run_protocol_cli(
        args,
        stdout=stdout,
        stderr=stderr,
        stdin="",
        cwd=tmp_path,
    )
    rendered = stdout.getvalue()
    assert stderr.getvalue() == ""
    assert exit_code == 0
    assert rendered.startswith("[search-fzf] q=hookruntime querySet=1")
    assert "Q=query:term(hookruntime)!fzf" in rendered
    assert "entries=owner-query(O,Q=>items+tests+dependency-usage)" in rendered
    assert "rank=Q,O,T frontier=Q.fzf,O.owner,T.tests" in rendered
    assert "|seed " not in rendered
