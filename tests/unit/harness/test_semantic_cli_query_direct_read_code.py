"""Direct-read query code output tests for the Python harness CLI."""

from __future__ import annotations

import io
from pathlib import Path

from python_lang_project_harness._cli import run_cli


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
