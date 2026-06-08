"""Direct-source-read code-output range preservation tests."""

from __future__ import annotations

import io
import json
import subprocess
from pathlib import Path

from python_lang_project_harness._cli import run_cli


def _write_demo_package(tmp_path: Path, lines: list[str]) -> None:
    package = tmp_path / "src" / "pkg"
    package.mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text(
        '\n[project]\nname = "demo-python"\nversion = "0.1.0"\nimport-names = ["pkg"]\n',
        encoding="utf-8",
    )
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "service.py").write_text("\n".join(lines), encoding="utf-8")


def test_cli_query_direct_source_read_code_preserves_header_when_range_overlaps_item(
    tmp_path: Path,
) -> None:
    _write_demo_package(
        tmp_path,
        [
            "import json",
            "from pathlib import Path",
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
            "src/pkg/service.py:1:5",
            "--code",
            "--workspace",
            str(tmp_path),
        ],
        stdout=stdout,
    )

    assert exit_code == 0
    assert stdout.getvalue() == (
        "import json\n"
        "from pathlib import Path\n"
        "\n"
        "def alpha(value: str) -> str:\n"
        "    return value.upper()\n"
    )


def test_cli_query_direct_source_read_source_option_reads_git_versions(
    tmp_path: Path,
) -> None:
    _write_demo_package(
        tmp_path,
        [
            "def marker() -> str:",
            "    return 'head'",
        ],
    )
    _run_git(tmp_path, "init")
    _run_git(tmp_path, "config", "user.email", "ci@example.invalid")
    _run_git(tmp_path, "config", "user.name", "CI")
    _run_git(
        tmp_path, "add", "pyproject.toml", "src/pkg/__init__.py", "src/pkg/service.py"
    )
    _run_git(tmp_path, "commit", "-m", "initial")
    (tmp_path / "src" / "pkg" / "service.py").write_text(
        "def marker() -> str:\n    return 'index'\n",
        encoding="utf-8",
    )
    _run_git(tmp_path, "add", "src/pkg/service.py")
    (tmp_path / "src" / "pkg" / "service.py").write_text(
        "def marker() -> str:\n    return 'worktree'\n",
        encoding="utf-8",
    )

    worktree_stdout = _query_source_stdout(tmp_path, source_args=())
    assert "'worktree'" in worktree_stdout
    assert "'index'" not in worktree_stdout
    assert "'head'" not in worktree_stdout

    index_stdout = _query_source_stdout(tmp_path, source_args=("--source", "index"))
    assert "'index'" in index_stdout
    assert "'worktree'" not in index_stdout
    assert "'head'" not in index_stdout

    head_stdout = _query_source_stdout(tmp_path, source_args=("--source", "head"))
    assert "'head'" in head_stdout
    assert "'worktree'" not in head_stdout
    assert "'index'" not in head_stdout

    stdout = io.StringIO()
    exit_code = run_cli(
        [
            "query",
            "--from-hook",
            "direct-source-read",
            "--selector",
            "src/pkg/service.py:1:2",
            "--source",
            "index",
            "--code",
            "--view",
            "read-packet",
            "--json",
            "--workspace",
            str(tmp_path),
        ],
        stdout=stdout,
    )

    assert exit_code == 0
    packet = json.loads(stdout.getvalue())
    assert packet["sourceVersion"] == "index"
    assert packet["repositoryRoot"] == str(tmp_path.resolve())
    assert len(packet["gitBlobOid"]) >= 40
    assert packet["sourceWindows"][0]["text"] == index_stdout.rstrip()


def _query_source_stdout(tmp_path: Path, *, source_args: tuple[str, ...]) -> str:
    stdout = io.StringIO()
    exit_code = run_cli(
        [
            "query",
            "--from-hook",
            "direct-source-read",
            "--selector",
            "src/pkg/service.py:1:2",
            *source_args,
            "--code",
            "--workspace",
            str(tmp_path),
        ],
        stdout=stdout,
    )
    assert exit_code == 0
    return stdout.getvalue()


def _run_git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    )
