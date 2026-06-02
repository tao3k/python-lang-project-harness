"""Direct-read query projection tests for Python line-range code output."""

from __future__ import annotations

import io
from pathlib import Path

from python_lang_project_harness._cli import run_cli


def test_query_from_hook_line_range_code_uses_ast_projection(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'sample'\nversion = '0.1.0'\n")
    src = tmp_path / "src"
    src.mkdir()
    (src / "sample.py").write_text(
        "\n".join(
            [
                "def first():",
                "    assert route == [",
                "        'py-harness',",
                "        'query',",
                "        '--selector',",
                "        'src/tools/report.py',",
                "        '.',",
                "    ]",
                "",
                "def second():",
                "    decision = classify_hook()",
                "",
            ]
        )
    )
    stdout = io.StringIO()

    exit_code = run_cli(
        [
            "query",
            "--from-hook",
            "direct-source-read",
            "--selector",
            "src/sample.py:5-10",
            "--code",
            str(tmp_path),
        ],
        stdout=stdout,
        cwd=tmp_path,
    )

    rendered = stdout.getvalue()
    assert exit_code == 0
    assert "def first" in rendered
    assert "def second" in rendered
    assert "'--selector'," not in rendered
