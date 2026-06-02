"""Direct-source-read query route tests for the Python semantic CLI."""

from __future__ import annotations

import io
import re
from pathlib import Path

from python_lang_project_harness import run_cli


def test_cli_query_direct_source_read_line_selector_returns_source_window(
    tmp_path: Path,
) -> None:
    package = tmp_path / "src" / "pkg"
    package.mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text(
        '\n[project]\nname = "demo-python"\nversion = "0.1.0"\nimport-names = ["pkg"]\n',
        encoding="utf-8",
    )
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "service.py").write_text(
        "\n".join(
            [
                "def alpha(value: str) -> str:",
                "    return value.upper()",
                "class Beta:",
                "    value: str",
            ]
        ),
        encoding="utf-8",
    )
    stdout = io.StringIO()

    exit_code = run_cli(
        [
            "query",
            "--from-hook",
            "direct-source-read",
            "--selector",
            "src/pkg/service.py:2-2",
            str(tmp_path),
        ],
        stdout=stdout,
    )

    rendered = stdout.getvalue()
    assert exit_code == 0
    assert re.search(
        r'^\[read-owner\] q=src/pkg/service\.py selector="src/pkg/service\.py:2-2" window=1',
        rendered,
        re.MULTILINE,
    )
    assert (
        "|read path=src/pkg/service.py item=alpha kind=function "
        "startLine=2 endLine=2 reason=direct-selector truncated=false"
    ) in rendered
    assert (
        "|code path=src/pkg/service.py startLine=2 endLine=2 "
        'reason=direct-source-read text="    return value.upper()"'
    ) in rendered
    assert "|item alpha" not in rendered
    assert "class Beta" not in rendered
