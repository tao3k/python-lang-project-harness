"""Stale worktree direct-read regression tests for the Python semantic CLI."""

from __future__ import annotations

from pathlib import Path

from python_lang_project_harness import run_python_project_harness
from python_lang_project_harness._semantic_search_item_direct_read import (
    owner_item_direct_read_lines,
)


def _write_demo_package(tmp_path: Path, lines: list[str]) -> None:
    package = tmp_path / "src" / "pkg"
    package.mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text(
        '\n[project]\nname = "demo-python"\nversion = "0.1.0"\nimport-names = ["pkg"]\n',
        encoding="utf-8",
    )
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "service.py").write_text("\n".join(lines), encoding="utf-8")


def test_direct_source_read_rereads_worktree_when_report_is_stale(
    tmp_path: Path,
) -> None:
    _write_demo_package(
        tmp_path,
        [
            "def alpha(value: str) -> str:",
            "    return value.upper()",
        ],
    )
    report = run_python_project_harness(tmp_path)
    (tmp_path / "src" / "pkg" / "service.py").write_text(
        "\n".join(
            [
                "def alpha(value: str) -> str:",
                "    return value.lower()",
            ]
        ),
        encoding="utf-8",
    )

    rendered = owner_item_direct_read_lines(
        report,
        tmp_path,
        "src/pkg/service.py",
        "",
        "src/pkg/service.py:2:2",
        code_only=True,
    )

    assert rendered == "    return value.lower()"
    assert "upper" not in rendered
