"""Filesystem-backed candidate discovery for Python semantic search."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

from ._constants import IGNORED_DIR_NAMES


def list_python_files(project_root: Path) -> tuple[Path, ...]:
    """Return scannable Python files below a project root."""

    fd = shutil.which("fd") or shutil.which("fdfind")
    if fd is not None:
        process = _run(
            [
                fd,
                "--color",
                "never",
                "-t",
                "f",
                "-e",
                "py",
                *(_fd_excludes()),
                ".",
                ".",
            ],
            cwd=project_root,
        )
        if process.returncode == 0:
            return trusted_tool_paths_from_output(project_root, process.stdout)
    return tuple(
        sorted(
            (
                path.resolve()
                for path in project_root.rglob("*.py")
                if not _ignored(path, project_root)
            ),
            key=lambda path: path.as_posix(),
        )
    )


def source_match_scores(project_root: Path, rg: str, term: str) -> dict[Path, int]:
    """Return candidate files scored by parser-likely source hits."""

    return source_match_scores_by_term(project_root, rg, (term,)).get(term, {})


def source_match_scores_by_term(
    project_root: Path,
    rg: str,
    terms: Sequence[str],
) -> dict[str, dict[Path, int]]:
    """Return source-hit scores for all query terms using one rg scan."""

    normalized_terms = tuple(dict.fromkeys(term for term in terms if term))
    if not normalized_terms:
        return {}
    process = _run(_rg_source_command(rg, normalized_terms), cwd=project_root)
    if process.returncode not in {0, 1}:
        return {}
    scores_by_term: dict[str, dict[Path, int]] = {
        term: {} for term in normalized_terms
    }
    for line in process.stdout.splitlines():
        _merge_source_line_scores(
            scores_by_term,
            project_root,
            line,
            normalized_terms,
        )
    return scores_by_term


def _merge_source_line_scores(
    scores_by_term: dict[str, dict[Path, int]],
    project_root: Path,
    line: str,
    terms: Sequence[str],
) -> None:
    parsed = _python_source_line(project_root, line)
    if parsed is None:
        return
    resolved, source = parsed
    for term in _matching_terms(source, terms):
        term_scores = scores_by_term[term]
        score = _source_line_score(source, term)
        term_scores[resolved] = min(term_scores.get(resolved, score), score)


def _python_source_line(project_root: Path, line: str) -> tuple[Path, str] | None:
    path, source = _split_rg_line(line)
    if path is None:
        return None
    resolved = project_root / path
    if resolved.suffix != ".py":
        return None
    return resolved, source


def _matching_terms(source: str, terms: Sequence[str]) -> tuple[str, ...]:
    folded_source = source.casefold()
    return tuple(term for term in terms if term.casefold() in folded_source)


def paths_from_output(project_root: Path, stdout: str) -> tuple[Path, ...]:
    """Return existing Python files named by command output."""

    paths: list[Path] = []
    for line in stdout.splitlines():
        if not line:
            continue
        path = Path(line)
        if not path.is_absolute():
            path = project_root / path
        resolved = path.resolve()
        if resolved.is_file() and resolved.suffix == ".py":
            paths.append(resolved)
    return tuple(sorted(set(paths), key=lambda path: path.as_posix()))


def trusted_tool_paths_from_output(project_root: Path, stdout: str) -> tuple[Path, ...]:
    """Return Python files from a trusted fd/rg file-list command."""

    paths = [
        path if path.is_absolute() else project_root / path
        for line in stdout.splitlines()
        if line
        for path in (Path(line),)
    ]
    return tuple(sorted(set(paths), key=lambda path: path.as_posix()))


def _rg_source_command(rg: str, terms: Sequence[str]) -> list[str]:
    expressions: list[str] = []
    for term in terms:
        expressions.extend(("-e", term))
    return [
        rg,
        "--color",
        "never",
        "-i",
        "-F",
        "-n",
        "--max-count",
        "50",
        "--glob",
        "*.py",
        *(_rg_excludes()),
        *expressions,
        ".",
    ]


def _run(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            cwd=cwd,
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(command, 124, "", "")


def _fd_excludes() -> tuple[str, ...]:
    args: list[str] = []
    for name in sorted(IGNORED_DIR_NAMES):
        args.extend(("-E", name))
    return tuple(args)


def _rg_excludes() -> tuple[str, ...]:
    args: list[str] = []
    for name in sorted(IGNORED_DIR_NAMES):
        args.extend(("--glob", f"!{name}/**"))
    return tuple(args)


def _ignored(path: Path, project_root: Path) -> bool:
    return any(part in IGNORED_DIR_NAMES for part in path.relative_to(project_root).parts)


def _split_rg_line(line: str) -> tuple[str | None, str]:
    first = line.find(":")
    if first == -1:
        return None, ""
    second = line.find(":", first + 1)
    if second == -1:
        return None, ""
    return line[:first], line[second + 1 :]


def _source_line_score(source_line: str, term: str) -> int:
    escaped = re.escape(term)
    if re.search(rf"^\s*(class|def)\s+{escaped}\b", source_line, re.IGNORECASE):
        return 0
    if re.search(rf"^\s*{escaped}\s*=", source_line, re.IGNORECASE):
        return 1
    if "__all__" in source_line:
        return 2
    return 3
