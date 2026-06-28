"""Fast exact-source query tests for the Python harness CLI."""

from __future__ import annotations

import io
import time
from pathlib import Path

from python_lang_project_harness import _cli_protocol, run_cli

_FAST_QUERY_BUDGET_MS = 250.0


def test_query_names_only_explicit_owner_bypasses_full_harness(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project = _write_fixture(tmp_path)

    def fail_full_harness(*_args: object, **_kwargs: object) -> None:
        raise AssertionError(
            "explicit owner names-only query should not run full harness"
        )

    monkeypatch.setattr(_cli_protocol, "_run_search_harness", fail_full_harness)

    elapsed_ms, output = _timed_cli(
        [
            "query",
            "src/example.py",
            "--term",
            "missing_owner",
            "--names-only",
            "--workspace",
            str(project),
        ],
        project,
    )

    assert "fallback=owner-top-items" in output
    assert "|item compute_value" in output
    assert "|item unrelated" in output
    assert elapsed_ms < _FAST_QUERY_BUDGET_MS


def test_query_code_selector_term_bypasses_full_harness(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project = _write_fixture(tmp_path)

    def fail_full_harness(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("selector code query should not run full harness")

    monkeypatch.setattr(_cli_protocol, "_run_search_harness", fail_full_harness)

    elapsed_ms, output = _timed_cli(
        [
            "query",
            "--selector",
            "src/example.py",
            "--term",
            "missing_owner",
            "--code",
            "--workspace",
            str(project),
        ],
        project,
    )

    assert "def compute_value(item: int) -> int:" in output
    assert "    return item + 1" in output
    assert "def unrelated() -> int:" in output
    assert elapsed_ms < _FAST_QUERY_BUDGET_MS


def test_query_items_selector_term_bypasses_full_harness(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project = _write_fixture(tmp_path)

    def fail_full_harness(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("selector item query should not run full harness")

    monkeypatch.setattr(_cli_protocol, "_run_search_harness", fail_full_harness)

    elapsed_ms, output = _timed_cli(
        [
            "query",
            "--selector",
            "src/example.py",
            "--term",
            "missing_owner",
            "--workspace",
            str(project),
        ],
        project,
    )

    assert "[search-owner]" in output
    assert "fallback=owner-top-items" in output
    assert "|item compute_value" in output
    assert "|item unrelated" in output
    assert elapsed_ms < _FAST_QUERY_BUDGET_MS


def _write_fixture(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    source_dir = project / "src"
    source_dir.mkdir(parents=True)
    (project / "pyproject.toml").write_text(
        '[project]\nname = "exact-query-fixture"\nversion = "0.1.0"\n',
        encoding="utf-8",
    )
    (source_dir / "example.py").write_text(
        "def compute_value(item: int) -> int:\n"
        "    return item + 1\n\n"
        "def unrelated() -> int:\n"
        "    return 0\n",
        encoding="utf-8",
    )
    return project


def _timed_cli(args: list[str], cwd: Path) -> tuple[float, str]:
    started = time.perf_counter()
    output = _run_cli(args, cwd)
    return (time.perf_counter() - started) * 1000.0, output


def _run_cli(args: list[str], cwd: Path) -> str:
    stdout = io.StringIO()
    stderr = io.StringIO()
    exit_code = run_cli(args, stdout=stdout, stderr=stderr, cwd=cwd)
    assert exit_code == 0, stderr.getvalue()
    return stdout.getvalue()
