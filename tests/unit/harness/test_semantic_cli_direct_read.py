"""Direct-source-read query route tests for the Python semantic CLI."""

from __future__ import annotations

import io
import json
import re
from pathlib import Path

from python_lang_project_harness import run_cli


def _write_demo_package(tmp_path: Path, lines: list[str]) -> None:
    package = tmp_path / "src" / "pkg"
    package.mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text(
        '\n[project]\nname = "demo-python"\nversion = "0.1.0"\nimport-names = ["pkg"]\n',
        encoding="utf-8",
    )
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "service.py").write_text("\n".join(lines), encoding="utf-8")


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
        "lineRange=2:2 read=src/pkg/service.py:2:2 "
        "next=direct-source-read reason=direct-selector truncated=false"
    ) in rendered
    assert "|code " not in rendered
    assert "return value.upper()" not in rendered
    assert "|item alpha" not in rendered
    assert "class Beta" not in rendered


def test_cli_query_direct_source_read_code_preserves_non_item_source_window(
    tmp_path: Path,
) -> None:
    _write_demo_package(
        tmp_path,
        [
            "# generated header",
            "# keep exact spacing",
            "",
            "def alpha(value: str) -> str:",
            "    return value.upper()",
        ],
    )
    stdout = io.StringIO()

    exit_code = run_cli(
        [
            "query",
            "--from-hook",
            "direct-source-read",
            "--selector",
            "src/pkg/service.py:1:2",
            "--code",
            "--workspace",
            str(tmp_path),
        ],
        stdout=stdout,
    )

    assert exit_code == 0
    assert stdout.getvalue() == "# generated header\n# keep exact spacing\n"


def test_cli_query_direct_source_read_read_packet_preserves_non_item_source_window(
    tmp_path: Path,
) -> None:
    _write_demo_package(
        tmp_path,
        [
            "# generated header",
            "# keep exact spacing",
            "",
            "def alpha(value: str) -> str:",
            "    return value.upper()",
        ],
    )
    stdout = io.StringIO()

    exit_code = run_cli(
        [
            "query",
            "--from-hook",
            "direct-source-read",
            "--selector",
            "src/pkg/service.py:1:2",
            "--code",
            "--view",
            "read-packet",
            "--json",
            "--workspace",
            str(tmp_path),
        ],
        stdout=stdout,
    )

    packet = json.loads(stdout.getvalue())
    window = packet["sourceWindows"][0]
    assert exit_code == 0
    assert packet["schemaId"] == "agent.semantic-protocols.semantic-read-packet"
    assert packet["languageId"] == "python"
    assert packet["outputMode"] == "read-packet"
    assert window["read"] == "src/pkg/service.py:1:2"
    assert window["text"] == "# generated header\n# keep exact spacing"
    assert window["lines"] == [
        {"number": 1, "text": "# generated header"},
        {"number": 2, "text": "# keep exact spacing"},
    ]
    assert "syntaxQueryRef" not in packet
    assert "itemName" not in window
    assert "itemKind" not in window


def test_cli_query_direct_source_read_wide_selector_returns_source_windows(
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
    assert rendered.startswith(
        '[read-owner] q=src/pkg/service.py selector="src/pkg/service.py:1:80" window=2'
    )
    assert "reason=wide-selector" not in rendered
    assert "|read path=src/pkg/service.py item=alpha kind=function" in rendered
    assert "read=src/pkg/service.py:1:2" in rendered
    assert "|read path=src/pkg/service.py item=beta kind=function" in rendered
    assert "read=src/pkg/service.py:4:5" in rendered
    assert "|code " not in rendered
    assert "return value.upper()" not in rendered
    assert "return value.lower()" not in rendered


def test_cli_query_direct_source_read_read_packet_wide_selector_emits_source_windows(
    tmp_path: Path,
) -> None:
    _write_demo_package(
        tmp_path,
        [
            "def alpha(value: str) -> str:",
            "    return value.upper()",
            "",
            "def beta(value: str) -> str:",
            "    return value.lower()",
        ],
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
            "--view",
            "read-packet",
            "--json",
            "--workspace",
            str(tmp_path),
        ],
        stdout=stdout,
    )

    packet = json.loads(stdout.getvalue())
    assert exit_code == 0
    assert packet["syntaxQueryRef"] == (
        "semantic-tree-sitter-query/python-owner-items.v1"
    )
    assert packet["syntaxMatchRefs"] == ["match.1", "match.2"]
    assert packet["syntaxCaptureRefs"] == ["capture.1", "capture.2"]
    assert "readPlan" not in packet
    windows = packet["sourceWindows"]
    assert len(windows) == 2
    assert windows[0]["read"] == "src/pkg/service.py:1:2"
    assert windows[0]["itemName"] == "alpha"
    assert (
        windows[0]["text"] == "def alpha(value: str) -> str:\n    return value.upper()"
    )
    assert windows[1]["read"] == "src/pkg/service.py:4:5"
    assert windows[1]["itemName"] == "beta"
    assert (
        windows[1]["text"] == "def beta(value: str) -> str:\n    return value.lower()"
    )


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
    assert "mode=range-frontier" in rendered
    assert "alg=symbol-frontier" in rendered
    assert "frontier=S.code" in rendered
    assert "reason=low-signal-window" in rendered
    assert "coverage=tail-only" in rendered
    assert "density=low" in rendered
    assert "|symbol item=render kind=function" in rendered
    assert "reason=parser-item" in rendered
    assert "|code " not in rendered


def test_cli_query_direct_source_read_code_flag_returns_source_for_wide_selector(
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
            "--workspace",
            str(tmp_path),
        ],
        stdout=stdout,
    )

    rendered = stdout.getvalue()
    assert exit_code == 0
    assert rendered.startswith("def alpha(value: str) -> str:\n")
    assert "\n\n" in rendered
    assert "def beta(value: str) -> str:\n" in rendered
    assert "return value.upper()" in rendered
    assert "return value.lower()" in rendered
    assert not rendered.startswith("[read-plan] ")
    assert "|code " not in rendered
