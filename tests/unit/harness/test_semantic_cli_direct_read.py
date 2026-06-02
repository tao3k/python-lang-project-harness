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
            "src/pkg/service.py:2:2",
            str(tmp_path),
        ],
        stdout=stdout,
    )

    rendered = stdout.getvalue()
    assert exit_code == 0
    assert re.search(
        r'^\[read-owner\] q=src/pkg/service\.py selector="src/pkg/service\.py:2:2" window=1',
        rendered,
        re.MULTILINE,
    )
    assert (
        "|read path=src/pkg/service.py item=alpha kind=function "
        "lineRange=2:2 reason=direct-selector truncated=false"
    ) in rendered
    assert (
        "|code path=src/pkg/service.py lineRange=2:2 "
        'reason=direct-source-read text="    return value.upper()"'
    ) in rendered
    assert "|item alpha" not in rendered
    assert "class Beta" not in rendered


def test_cli_query_direct_source_read_wide_selector_returns_outline_without_code(
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
                "",
                "def beta(value: str) -> str:",
                "    return value.lower()",
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
            "src/pkg/service.py:1:80",
            str(tmp_path),
        ],
        stdout=stdout,
    )

    rendered = stdout.getvalue()
    assert exit_code == 0
    assert rendered.startswith("[read-plan] ")
    assert "mode=range-outline" in rendered
    assert "reason=wide-selector" in rendered
    assert "|code " not in rendered
    assert "|symbol item=alpha kind=function" in rendered
    assert "|symbol item=beta kind=function" in rendered


def test_cli_query_direct_source_read_low_signal_tail_returns_outline_without_code(
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
                "def render(value: str) -> str:",
                "    return (",
                "        value",
                "    )",
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
            "src/pkg/service.py:4:4",
            str(tmp_path),
        ],
        stdout=stdout,
    )

    rendered = stdout.getvalue()
    assert exit_code == 0
    assert rendered.startswith("[read-plan] ")
    assert "mode=range-outline" in rendered
    assert "reason=low-signal-window" in rendered
    assert "coverage=tail-only" in rendered
    assert "density=low" in rendered
    assert "|symbol item=render kind=function" in rendered
    assert "|code " not in rendered


def test_cli_query_direct_source_read_code_flag_still_uses_read_plan_for_wide_selector(
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
                "",
                "def beta(value: str) -> str:",
                "    return value.lower()",
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
            "src/pkg/service.py:1:80",
            "--code",
            str(tmp_path),
        ],
        stdout=stdout,
    )

    rendered = stdout.getvalue()
    assert exit_code == 0
    assert rendered.startswith("[read-plan] ")
    assert "reason=wide-selector" in rendered
    assert "|code " not in rendered
    assert "return value.upper()" not in rendered
