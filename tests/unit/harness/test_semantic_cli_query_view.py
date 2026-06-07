"""Query view validation tests for the Python semantic CLI."""

from __future__ import annotations

import io
from pathlib import Path

from python_lang_project_harness import run_cli


def test_cli_query_rejects_document_metadata_view_for_python_provider(
    tmp_path: Path,
) -> None:
    stdout = io.StringIO()
    stderr = io.StringIO()

    exit_code = run_cli(
        [
            "query",
            "--term",
            "result_to_packet",
            "--view",
            "metadata",
            "--code",
            str(tmp_path),
        ],
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 2
    assert stdout.getvalue() == ""
    assert "--view metadata is document-only for asp md/org query" in stderr.getvalue()
    assert "Python query uses search --view seeds" in stderr.getvalue()
    assert "query <owner-path> --term <symbol> --code" in stderr.getvalue()
