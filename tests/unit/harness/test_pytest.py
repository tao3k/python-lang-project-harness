from __future__ import annotations

import subprocess
import sys
from typing import TYPE_CHECKING

from python_lang_parser import PythonDiagnosticSeverity
from python_lang_project_harness import PythonHarnessConfig, python_project_harness_test
from python_lang_project_harness.pytest import (
    python_project_harness_test as facade_python_project_harness_test,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_python_project_harness_test_returns_pytest_collectable_callable(
    tmp_path: Path,
) -> None:
    src = tmp_path / "src"
    tests = tmp_path / "tests" / "unit"
    src.mkdir()
    tests.mkdir(parents=True)
    (src / "library.py").write_text(
        '"""Library docs."""\n\nVALUE = 1\n', encoding="utf-8"
    )
    (tests / "test_library.py").write_text(
        "def test_value() -> None:\n    assert True\n",
        encoding="utf-8",
    )

    harness_test = python_project_harness_test(tmp_path)

    assert harness_test.__name__ == "test_python_project_harness_policy"
    assert harness_test.__qualname__ == "test_python_project_harness_policy"
    harness_test()


def test_python_project_harness_test_defaults_to_current_project_root(
    tmp_path: Path,
    monkeypatch,
) -> None:
    src = tmp_path / "src"
    tests = tmp_path / "tests" / "unit"
    src.mkdir()
    tests.mkdir(parents=True)
    (src / "library.py").write_text('"""Library docs."""\n', encoding="utf-8")
    (tests / "test_library.py").write_text(
        "def test_value() -> None:\n    assert True\n",
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)

    harness_test = python_project_harness_test()

    harness_test()


def test_public_pytest_facade_exposes_collectable_helper() -> None:
    assert facade_python_project_harness_test is python_project_harness_test


def test_python_project_harness_test_blocks_with_compact_snapshot(
    tmp_path: Path,
) -> None:
    src = tmp_path / "src"
    src.mkdir()
    source = src / "library.py"
    source.write_text('def run() -> None:\n    print("debug")\n', encoding="utf-8")
    harness_test = python_project_harness_test(tmp_path)

    try:
        harness_test()
    except AssertionError as error:
        message = str(error)
    else:
        raise AssertionError("pytest harness callable should block policy findings")

    assert "[PY-MOD-R002] Warning: Library module uses bare print" in message
    assert str(source) in message
    assert "[advice]" in message


def test_python_project_harness_test_can_disable_agent_advice(
    tmp_path: Path,
) -> None:
    src = tmp_path / "src"
    src.mkdir()
    source = src / "library.py"
    source.write_text('def run() -> None:\n    print("debug")\n', encoding="utf-8")
    harness_test = python_project_harness_test(tmp_path, include_advice=False)

    try:
        harness_test()
    except AssertionError as error:
        message = str(error)
    else:
        raise AssertionError("pytest harness callable should block policy findings")

    assert "[PY-MOD-R002] Warning: Library module uses bare print" in message
    assert "[advice]" not in message


def test_python_project_harness_test_honors_embedded_options(
    tmp_path: Path,
) -> None:
    lib = tmp_path / "lib"
    tests = tmp_path / "tests" / "unit"
    lib.mkdir()
    tests.mkdir(parents=True)
    (lib / "library.py").write_text(
        'def run() -> None:\n    print("debug")\n',
        encoding="utf-8",
    )
    (tests / "test_bad.py").write_text("def broken(:\n    pass\n", encoding="utf-8")

    harness_test = python_project_harness_test(
        tmp_path,
        severities=frozenset({PythonDiagnosticSeverity.ERROR}),
        include_tests=False,
        source_dir_names=("lib",),
        test_name="test_custom_python_project_policy",
    )

    assert harness_test.__name__ == "test_custom_python_project_policy"
    assert harness_test.__qualname__ == "test_custom_python_project_policy"
    harness_test()


def test_python_project_harness_test_honors_configured_project_scope(
    tmp_path: Path,
) -> None:
    lib = tmp_path / "lib"
    tests = tmp_path / "tests" / "unit"
    lib.mkdir()
    tests.mkdir(parents=True)
    (lib / "library.py").write_text('"""Library docs."""\n', encoding="utf-8")
    (tests / "test_bad.py").write_text("def broken(:\n    pass\n", encoding="utf-8")

    harness_test = python_project_harness_test(
        tmp_path,
        config=PythonHarnessConfig(source_dir_names=("lib",), include_tests=False),
    )

    harness_test()


def test_pytest_plugin_collects_harness_item_from_dev_dependency(
    tmp_path: Path,
) -> None:
    _write_clean_project(tmp_path)

    result = _run_pytest_plugin(tmp_path, "--python-project-harness")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "2 passed" in result.stdout


def test_pytest_plugin_is_quiet_without_enable_option(
    tmp_path: Path,
) -> None:
    _write_clean_project(tmp_path)

    result = _run_pytest_plugin(tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "1 passed" in result.stdout


def test_pytest_plugin_can_be_enabled_from_pyproject_addopts(
    tmp_path: Path,
) -> None:
    _write_clean_project(tmp_path)
    (tmp_path / "pyproject.toml").write_text(
        """
[tool.pytest.ini_options]
addopts = ["--python-project-harness"]
""".lstrip(),
        encoding="utf-8",
    )

    result = _run_pytest_plugin(tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "2 passed" in result.stdout


def test_pytest_plugin_runs_without_downstream_test_files(
    tmp_path: Path,
) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "library.py").write_text('"""Library docs."""\n', encoding="utf-8")

    result = _run_pytest_plugin(tmp_path, "--python-project-harness")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "1 passed" in result.stdout


def test_pytest_plugin_reports_compact_harness_failure(
    tmp_path: Path,
) -> None:
    src = tmp_path / "src"
    tests = tmp_path / "tests" / "unit"
    src.mkdir()
    tests.mkdir(parents=True)
    (src / "library.py").write_text(
        'def run() -> None:\n    print("debug")\n',
        encoding="utf-8",
    )
    (tests / "test_placeholder.py").write_text(
        "def test_placeholder() -> None:\n    assert True\n",
        encoding="utf-8",
    )

    result = _run_pytest_plugin(tmp_path, "--python-project-harness")

    assert result.returncode == 1
    assert "[PY-MOD-R002] Warning: Library module uses bare print" in result.stdout
    assert "Required:" in result.stdout


def test_pytest_plugin_honors_dev_dependency_options(
    tmp_path: Path,
) -> None:
    lib = tmp_path / "lib"
    tests = tmp_path / "tests" / "unit"
    lib.mkdir()
    tests.mkdir(parents=True)
    (lib / "library.py").write_text(
        'def run() -> None:\n    print("debug")\n',
        encoding="utf-8",
    )
    (tests / "test_bad.py").write_text(
        "def test_bad() -> None:\n    assert True\n",
        encoding="utf-8",
    )
    (tests / "test_placeholder.py").write_text(
        "def test_placeholder() -> None:\n    assert True\n",
        encoding="utf-8",
    )

    result = _run_pytest_plugin(
        tmp_path,
        "--python-project-harness",
        "--python-project-harness-source-dir=lib",
        "--python-project-harness-no-tests",
        "--python-project-harness-error-only",
    )

    assert result.returncode == 0, result.stdout + result.stderr


def _write_clean_project(project_root: Path) -> None:
    src = project_root / "src"
    tests = project_root / "tests" / "unit"
    src.mkdir()
    tests.mkdir(parents=True)
    (src / "library.py").write_text('"""Library docs."""\n', encoding="utf-8")
    (tests / "test_placeholder.py").write_text(
        "def test_placeholder() -> None:\n    assert True\n",
        encoding="utf-8",
    )


def _run_pytest_plugin(project_root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", *args],
        cwd=project_root,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_python_project_harness_test_honors_extra_project_paths(
    tmp_path: Path,
) -> None:
    src = tmp_path / "src"
    tools = tmp_path / "tools"
    src.mkdir()
    tools.mkdir()
    (src / "library.py").write_text('"""Library docs."""\n', encoding="utf-8")
    (tools / "check.py").write_text('"""Check docs."""\n', encoding="utf-8")

    harness_test = python_project_harness_test(
        tmp_path,
        extra_path_names=("tools",),
    )

    harness_test()
