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


def test_project_policy_requires_pytest_gate_for_harness_dev_dependency(
    tmp_path: Path,
) -> None:
    _write_pyproject(
        tmp_path,
        """
[project]
name = "example-pkg"
requires-python = ">=3.12"

[dependency-groups]
test = [
    "python-lang-project-harness[pytest]>=0.1.0",
]
""",
    )

    report = run_python_project_harness(tmp_path)

    assert [
        (finding.rule_id, finding.location.path) for finding in report.findings
    ] == [
        ("PY-PROJ-R010", str(tmp_path / "pyproject.toml")),
    ]


def test_project_policy_accepts_pytest_addopts_gate(tmp_path: Path) -> None:
    _write_pyproject(
        tmp_path,
        """
[project]
name = "example-pkg"
requires-python = ">=3.12"

[dependency-groups]
test = [
    "python-lang-project-harness[pytest]>=0.1.0",
]

[tool.pytest.ini_options]
addopts = ["--python-project-harness"]
""",
    )

    report = run_python_project_harness(tmp_path)

    assert not any(finding.rule_id == "PY-PROJ-R010" for finding in report.findings)


def test_project_policy_accepts_explicit_pytest_helper_gate(tmp_path: Path) -> None:
    _write_pyproject(
        tmp_path,
        """
[project]
name = "example-pkg"
requires-python = ">=3.12"

[dependency-groups]
test = [
    "python-lang-project-harness[pytest]>=0.1.0",
]
""",
    )
    tests = tmp_path / "tests" / "unit"
    tests.mkdir(parents=True)
    (tests / "test_harness_policy.py").write_text(
        "from python_lang_project_harness.pytest import python_project_harness_test\n"
        "test_python_project_harness_policy = python_project_harness_test()\n",
        encoding="utf-8",
    )

    report = run_python_project_harness(tmp_path)

    assert not any(finding.rule_id == "PY-PROJ-R010" for finding in report.findings)


def _write_pyproject(project_root: Path, content: str) -> None:
    (project_root / "src").mkdir()
    (project_root / "pyproject.toml").write_text(
        content.lstrip(),
        encoding="utf-8",
    )
