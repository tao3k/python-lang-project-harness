"""Direct-read query code output tests for the Python harness CLI."""

from __future__ import annotations

import io
import time
from pathlib import Path

import pytest

from python_lang_project_harness._cli import run_cli

FAST_QUERY_BUDGET_SECONDS = 0.25


def test_query_from_hook_line_range_code_uses_selector_window() -> None:
    project_root = Path(__file__).resolve().parents[3]
    stdout = io.StringIO()

    exit_code = run_cli(
        [
            "query",
            "--from-hook",
            "direct-source-read",
            "--selector",
            "src/python_lang_project_harness/_cli_query.py:1-120",
            "--code",
            str(project_root),
        ],
        stdout=stdout,
        cwd=project_root,
    )

    rendered = stdout.getvalue()
    assert exit_code == 0
    assert "def run_query_command(" in rendered
    assert "[read-owner]" not in rendered
    assert "owner_item_direct_read_lines" in rendered


def test_query_selector_code_uses_fast_range_without_full_harness(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_path = tmp_path / "tests" / "test_query_packet.py"
    source_path.parent.mkdir(parents=True)
    source_path.write_text(
        '"""Validate document query packet schema examples."""\n\n'
        "def test_content_blocks():\n"
        "    assert 'contentBlocks'\n",
        encoding="utf-8",
    )

    from python_lang_project_harness import _cli_protocol

    def fail_full_harness(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("full harness should not run for exact selector code")

    monkeypatch.setattr(_cli_protocol, "_run_search_harness", fail_full_harness)
    stdout = io.StringIO()

    exit_code = run_cli(
        [
            "query",
            "--selector",
            "tests/test_query_packet.py:1-4",
            "--term",
            "contentBlocks",
            "--code",
            str(tmp_path),
        ],
        stdout=stdout,
        cwd=tmp_path,
    )

    rendered = stdout.getvalue()
    assert exit_code == 0
    assert rendered.startswith('"""Validate document query packet schema examples."""')
    assert "contentBlocks" in rendered


def test_query_direct_read_line_range_code_uses_fast_path_without_full_harness(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_path = tmp_path / "src" / "package" / "module.py"
    source_path.parent.mkdir(parents=True)
    source_path.write_text(
        "def first():\n    return 'skip'\n\ndef selected():\n    return 'direct'\n",
        encoding="utf-8",
    )

    from python_lang_project_harness import _cli_protocol

    def fail_full_harness(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("full harness should not run for direct-read range code")

    monkeypatch.setattr(_cli_protocol, "_run_search_harness", fail_full_harness)
    stdout = io.StringIO()

    started_at = time.perf_counter()
    exit_code = run_cli(
        [
            "query",
            "--from-hook",
            "direct-source-read",
            "--selector",
            "src/package/module.py:4-5",
            "--code",
            str(tmp_path),
        ],
        stdout=stdout,
        cwd=tmp_path,
    )
    elapsed = time.perf_counter() - started_at

    assert exit_code == 0
    assert stdout.getvalue() == "def selected():\n    return 'direct'\n"
    assert elapsed < FAST_QUERY_BUDGET_SECONDS


def test_query_direct_read_file_selector_uses_fast_path_without_full_harness(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_path = tmp_path / "tests" / "test_docs_rfc_skill_contracts.py"
    source_path.parent.mkdir(parents=True)
    source_text = (
        '"""Contract docs."""\n\n'
        "def test_skill_mentions_hook_install():\n"
        "    assert 'asp hook install'\n"
    )
    source_path.write_text(source_text, encoding="utf-8")
    invalid_path = tmp_path / "src" / "invalid.py"
    invalid_path.parent.mkdir(parents=True)
    invalid_path.write_text("def broken(:\n", encoding="utf-8")

    from python_lang_project_harness import _cli_protocol

    def fail_full_harness(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("full harness should not run for direct-read file code")

    monkeypatch.setattr(_cli_protocol, "_run_search_harness", fail_full_harness)
    stdout = io.StringIO()

    started_at = time.perf_counter()
    exit_code = run_cli(
        [
            "query",
            "--from-hook",
            "direct-source-read",
            "--selector",
            "tests/test_docs_rfc_skill_contracts.py",
            "--code",
            str(tmp_path),
        ],
        stdout=stdout,
        cwd=tmp_path,
    )
    elapsed = time.perf_counter() - started_at

    assert exit_code == 0
    assert stdout.getvalue() == source_text
    assert elapsed < FAST_QUERY_BUDGET_SECONDS
