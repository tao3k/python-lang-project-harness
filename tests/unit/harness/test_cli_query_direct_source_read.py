"""Direct-source-read query CLI contract tests."""

from __future__ import annotations

import io
from pathlib import Path

from python_lang_project_harness import run_cli


def test_cli_query_direct_source_read_code_uses_selector_without_project_root(
    tmp_path: Path,
) -> None:
    source = tmp_path / "tests" / "unit" / "example.py"
    source.parent.mkdir(parents=True)
    source_text = "def target(value: int) -> int:\n    return value + 1\n"
    source.write_text(source_text, encoding="utf-8")

    for args, cwd in (
        (
            [
                "query",
                "--from-hook",
                "direct-source-read",
                "--selector",
                "tests/unit/example.py:1-2",
                "--code",
            ],
            tmp_path,
        ),
        (
            [
                "query",
                "--from-hook",
                "direct-source-read",
                "--selector",
                "tests/unit/example.py:1-2",
                "--workspace",
                str(tmp_path),
                "--code",
            ],
            tmp_path / "outside",
        ),
        (
            [
                "query",
                "--from-hook",
                "direct-source-read",
                "--selector",
                f"{source}:1-2",
                "--code",
            ],
            tmp_path / "outside",
        ),
    ):
        Path(cwd).mkdir(exist_ok=True)
        stdout = io.StringIO()

        exit_code = run_cli(args, stdout=stdout, cwd=Path(cwd))

        assert exit_code == 0
        assert stdout.getvalue() == source_text


def test_cli_query_code_rejects_trailing_project_root(tmp_path: Path) -> None:
    source = tmp_path / "tests" / "unit" / "example.py"
    source.parent.mkdir(parents=True)
    source.write_text("def target() -> None:\n    pass\n", encoding="utf-8")

    cases = (
        [
            "query",
            "--from-hook",
            "direct-source-read",
            "--selector",
            "tests/unit/example.py:1-2",
            "--code",
            str(tmp_path),
        ],
        [
            "query",
            "tests/unit/example.py",
            "--term",
            "target",
            "--code",
            str(tmp_path),
        ],
        [
            "query",
            "--treesitter-query",
            "(function_definition name: (identifier) @function.name)",
            "--selector",
            "tests/unit/example.py:1-2",
            "--code",
            str(tmp_path),
        ],
        [
            "search",
            "owner",
            "tests/unit/example.py",
            "items",
            "--query",
            "target",
            "--code",
            str(tmp_path),
        ],
    )

    for args in cases:
        stderr = io.StringIO()

        exit_code = run_cli(args, stdout=io.StringIO(), stderr=stderr, cwd=tmp_path)

        assert exit_code == 2
        assert "does not accept a trailing PROJECT_ROOT" in stderr.getvalue()
