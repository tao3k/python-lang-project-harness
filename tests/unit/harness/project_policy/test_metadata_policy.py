from __future__ import annotations

from typing import TYPE_CHECKING

from python_lang_project_harness import run_python_project_harness

if TYPE_CHECKING:
    from pathlib import Path


def test_project_policy_blocks_project_table_without_name(tmp_path: Path) -> None:
    _write_pyproject(
        tmp_path,
        """
[project]
requires-python = ">=3.12"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
""",
    )

    report = run_python_project_harness(tmp_path)

    assert [
        (finding.rule_id, finding.location.path) for finding in report.findings
    ] == [
        ("PY-PROJ-R005", str(tmp_path / "pyproject.toml")),
    ]


def test_project_policy_blocks_project_table_without_requires_python(
    tmp_path: Path,
) -> None:
    _write_pyproject(
        tmp_path,
        """
[project]
name = "example-pkg"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
""",
    )

    report = run_python_project_harness(tmp_path)

    assert [
        (finding.rule_id, finding.location.path) for finding in report.findings
    ] == [
        ("PY-PROJ-R006", str(tmp_path / "pyproject.toml")),
    ]


def test_project_policy_blocks_build_system_table_without_requires(
    tmp_path: Path,
) -> None:
    _write_pyproject(
        tmp_path,
        """
[project]
name = "example-pkg"
requires-python = ">=3.12"

[build-system]
build-backend = "hatchling.build"
""",
    )

    report = run_python_project_harness(tmp_path)

    assert [
        (finding.rule_id, finding.location.path) for finding in report.findings
    ] == [
        ("PY-PROJ-R007", str(tmp_path / "pyproject.toml")),
    ]


def test_project_policy_allows_tool_only_pyproject(tmp_path: Path) -> None:
    _write_pyproject(
        tmp_path,
        """
[tool.pytest.ini_options]
addopts = ["--import-mode=importlib"]
""",
    )

    report = run_python_project_harness(tmp_path)

    assert not any(
        finding.rule_id.startswith("PY-PROJ-") for finding in report.findings
    )


def _write_pyproject(project_root: Path, content: str) -> None:
    (project_root / "src").mkdir()
    (project_root / "pyproject.toml").write_text(
        content.lstrip(),
        encoding="utf-8",
    )
