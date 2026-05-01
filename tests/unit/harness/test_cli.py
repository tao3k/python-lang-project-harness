from __future__ import annotations

import io
import json
from typing import TYPE_CHECKING

from python_lang_project_harness import run_cli

if TYPE_CHECKING:
    from pathlib import Path


def test_cli_renders_compact_text_by_default(tmp_path: Path) -> None:
    package = tmp_path / "src" / "pkg"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text('"""Package docs."""\n', encoding="utf-8")

    stdout = io.StringIO()
    stderr = io.StringIO()

    exit_code = run_cli([str(tmp_path)], stdout=stdout, stderr=stderr)

    assert exit_code == 0
    assert stderr.getvalue() == ""
    assert stdout.getvalue().startswith("[ok]")
    assert "Files: 1 Parsed: 1" in stdout.getvalue()


def test_cli_json_flag_renders_structured_report(tmp_path: Path) -> None:
    package = tmp_path / "src" / "pkg"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text('"""Package docs."""\n', encoding="utf-8")
    stdout = io.StringIO()

    exit_code = run_cli(["--json", str(tmp_path)], stdout=stdout)
    payload = json.loads(stdout.getvalue())

    assert exit_code == 0
    assert payload["is_clean"] is True
    assert payload["file_count"] == 1
    assert payload["project_scope"]["project_root"] == str(tmp_path)


def test_cli_keeps_agent_advice_non_blocking(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "service.py").write_text(
        "def build(value):\n    return value\n", encoding="utf-8"
    )
    stdout = io.StringIO()

    exit_code = run_cli([str(tmp_path)], stdout=stdout)

    assert exit_code == 0
    assert "[advice]" in stdout.getvalue()
    assert "PY-AGENT-R001" in stdout.getvalue()


def test_cli_exits_nonzero_for_blocking_findings(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "service.py").write_text(
        'def build() -> None:\n    print("debug")\n',
        encoding="utf-8",
    )
    stdout = io.StringIO()

    exit_code = run_cli([str(tmp_path)], stdout=stdout)

    assert exit_code == 1
    assert "PY-MOD-R002" in stdout.getvalue()
    assert stdout.getvalue().startswith("[PY-MOD-R002] Warning")


def test_cli_can_disable_policy_rule_ids(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "service.py").write_text(
        'def run() -> None:\n    print("debug")\n',
        encoding="utf-8",
    )
    stdout = io.StringIO()

    exit_code = run_cli(
        ["--disable-rule", "PY-MOD-R002", str(tmp_path)],
        stdout=stdout,
    )

    assert exit_code == 0
    assert "PY-MOD-R002" not in stdout.getvalue()


def test_cli_loads_project_policy_config_from_pyproject(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (tmp_path / "pyproject.toml").write_text(
        """
[tool.python-lang-project-harness]
disabled_rule_ids = ["PY-MOD-R002"]
""".lstrip(),
        encoding="utf-8",
    )
    (src / "service.py").write_text(
        'def run() -> None:\n    print("debug")\n',
        encoding="utf-8",
    )
    stdout = io.StringIO()

    exit_code = run_cli([str(tmp_path)], stdout=stdout)

    assert exit_code == 0
    assert "PY-MOD-R002" not in stdout.getvalue()


def test_cli_can_promote_policy_rule_ids(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "service.py").write_text(
        "def build(value):\n    return value\n",
        encoding="utf-8",
    )
    stdout = io.StringIO()

    exit_code = run_cli(["--block-rule", "PY-AGENT-R001", str(tmp_path)], stdout=stdout)

    assert exit_code == 1
    assert "PY-AGENT-R001" in stdout.getvalue()
    assert stdout.getvalue().startswith("[PY-AGENT-R001] Info")


def test_cli_help_and_argument_errors_are_stable(tmp_path: Path) -> None:
    help_stdout = io.StringIO()
    error_stderr = io.StringIO()

    assert run_cli(["--help"], stdout=help_stdout) == 0
    assert "python-project-harness [--json] [--no-tests]" in help_stdout.getvalue()
    assert run_cli(["--bogus"], stderr=error_stderr) == 2
    assert "unknown option: --bogus" in error_stderr.getvalue()
    assert run_cli([str(tmp_path), str(tmp_path)], stderr=io.StringIO()) == 2


def test_cli_scope_flags_customize_project_paths(tmp_path: Path) -> None:
    lib = tmp_path / "lib"
    tools = tmp_path / "tools"
    tests = tmp_path / "tests" / "unit"
    lib.mkdir()
    tools.mkdir()
    tests.mkdir(parents=True)
    (lib / "service.py").write_text('"""Service docs."""\n', encoding="utf-8")
    (tools / "check.py").write_text('"""Check docs."""\n', encoding="utf-8")
    (tests / "test_bad.py").write_text("def broken(:\n    pass\n", encoding="utf-8")
    stdout = io.StringIO()

    exit_code = run_cli(
        [
            "--source-dir",
            "lib",
            "--extra-path",
            "tools",
            "--no-tests",
            str(tmp_path),
        ],
        stdout=stdout,
    )

    assert exit_code == 0
    assert "Files: 2 Parsed: 2" in stdout.getvalue()
    assert str(lib) in stdout.getvalue()
    assert str(tools) in stdout.getvalue()


def test_cli_no_tests_skips_test_parser_discovery(tmp_path: Path) -> None:
    src = tmp_path / "src"
    tests = tmp_path / "tests" / "unit"
    src.mkdir()
    tests.mkdir(parents=True)
    (src / "service.py").write_text('"""Service docs."""\n', encoding="utf-8")
    (tests / "test_bad.py").write_text("def broken(:\n    pass\n", encoding="utf-8")
    stdout = io.StringIO()

    exit_code = run_cli(["--no-tests", str(tmp_path)], stdout=stdout)

    assert exit_code == 0
    assert "Files: 1 Parsed: 1" in stdout.getvalue()


def test_cli_scope_flag_values_are_required() -> None:
    stderr = io.StringIO()

    assert run_cli(["--source-dir"], stderr=stderr) == 2
    assert "missing value for --source-dir" in stderr.getvalue()
    assert run_cli(["--disable-rule"], stderr=io.StringIO()) == 2


def test_cli_defaults_to_current_working_directory(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "service.py").write_text('"""Service docs."""\n', encoding="utf-8")
    stdout = io.StringIO()

    exit_code = run_cli((), stdout=stdout, cwd=tmp_path)

    assert exit_code == 0
    assert str(tmp_path) in stdout.getvalue()
