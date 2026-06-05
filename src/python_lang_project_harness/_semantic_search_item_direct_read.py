"""Direct-source-read rendering for Python owner item selectors."""

from __future__ import annotations

import subprocess
import tokenize
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ._semantic_search_direct_read_render import (
    direct_read_item_window,
    direct_read_range_window,
    render_direct_read_packet,
    render_direct_read_windows,
)
from ._semantic_search_items import (
    _module_for_owner,
    _selector_line_range,
    _selector_range_items,
)

if TYPE_CHECKING:
    from ._project_policy_context import PythonHarnessReport


def owner_item_direct_read_lines(
    report: PythonHarnessReport,
    project_root: Path,
    owner_path: str,
    item_query: str,
    selector: str,
    *,
    code_only: bool = False,
    source_version: str = "worktree",
) -> str:
    """Return exact source windows for a hook direct-source-read selector."""

    del item_query
    source, selector_range, windows = _direct_read_windows(
        report, project_root, owner_path, selector, source_version
    )
    if code_only and _direct_read_code_should_preserve_range(windows, selector_range):
        windows = [direct_read_range_window(source.lines, owner_path, selector_range)]
    return render_direct_read_windows(
        owner_path=owner_path,
        selector=selector,
        source_lines=source.lines,
        selector_range=selector_range,
        windows=windows,
        code_only=code_only,
    )


def owner_item_direct_read_packet(
    report: PythonHarnessReport,
    project_root: Path,
    owner_path: str,
    item_query: str,
    selector: str,
    *,
    source_version: str = "worktree",
) -> dict[str, Any]:
    """Return the structured read packet for a direct-source-read selector."""

    del item_query
    source, selector_range, windows = _direct_read_windows(
        report, project_root, owner_path, selector, source_version
    )
    from ._semantic_syntax_refs import (
        annotate_python_owner_item_syntax_refs,
        attach_python_syntax_refs,
    )

    syntax_refs = annotate_python_owner_item_syntax_refs(
        [
            window["item"]
            for window in windows
            if isinstance(window.get("item"), dict)
            and window["item"].get("name")
            and window["item"].get("kind")
        ]
    )
    packet = render_direct_read_packet(
        project_root=project_root,
        owner_path=owner_path,
        selector=selector,
        selector_range=selector_range,
        windows=windows,
        source_version=source.version,
        repository_root=source.repository_root,
        git_blob_oid=source.git_blob_oid,
    )
    attach_python_syntax_refs(packet, syntax_refs)
    return packet


@dataclass(frozen=True, slots=True)
class _DirectReadSource:
    lines: list[str]
    version: str
    matches_report: bool = True
    repository_root: str | None = None
    git_blob_oid: str | None = None


def _direct_read_windows(
    report: PythonHarnessReport,
    project_root: Path,
    owner_path: str,
    selector: str,
    source_version: str,
) -> tuple[_DirectReadSource, tuple[int, int], list[dict[str, Any]]]:
    selector_range = _selector_line_range(selector, owner_path)
    module = _module_for_owner(report, project_root, owner_path)
    if selector_range is None or module is None:
        raise ValueError(
            f"direct-source-read selector resolved to no parser-owned source: {owner_path}"
        )
    source = _direct_read_source(
        project_root, owner_path, module.source_lines, source_version
    )
    if selector_range[0] > len(source.lines):
        raise ValueError(
            f"direct-source-read selector is outside owner source: {owner_path}"
        )
    if source.version != "worktree" or not source.matches_report:
        return (
            source,
            selector_range,
            [direct_read_range_window(source.lines, owner_path, selector_range)],
        )
    items = _selector_range_items(report, project_root, owner_path, selector_range)
    if items:
        windows = [
            direct_read_item_window(source.lines, item, selector_range)
            for item in items
        ]
    else:
        windows = [direct_read_range_window(source.lines, owner_path, selector_range)]
    return source, selector_range, windows


def _direct_read_source(
    project_root: Path,
    owner_path: str,
    worktree_lines: Sequence[str],
    source_version: str,
) -> _DirectReadSource:
    if source_version == "worktree":
        source_path = _direct_read_source_path(project_root, owner_path)
        try:
            with tokenize.open(source_path) as handle:
                source_text = handle.read()
        except OSError as error:
            raise ValueError(
                f"direct-source-read worktree source could not be read: {source_path}"
            ) from error
        source_lines = source_text.splitlines()
        return _DirectReadSource(
            lines=source_lines,
            version="worktree",
            matches_report=tuple(source_lines) == tuple(worktree_lines),
        )
    repository_root, repo_relative_path = _git_source_locator(project_root, owner_path)
    object_name = _git_object_name(source_version, repo_relative_path)
    source_text = _git_output(repository_root, "show", object_name)
    git_blob_oid = _git_output(repository_root, "rev-parse", object_name).strip()
    return _DirectReadSource(
        lines=source_text.splitlines(),
        version=source_version,
        repository_root=str(repository_root),
        git_blob_oid=git_blob_oid,
    )


def _git_source_locator(project_root: Path, owner_path: str) -> tuple[Path, str]:
    repository_root = Path(
        _git_output(project_root, "rev-parse", "--show-toplevel").strip()
    ).resolve()
    source_path = _direct_read_source_path(project_root, owner_path).resolve()
    try:
        repo_relative_path = source_path.relative_to(repository_root)
    except ValueError as error:
        raise ValueError(
            "query --source git reads require "
            f"{source_path} to be under repository root {repository_root}"
        ) from error
    return repository_root, repo_relative_path.as_posix()


def _direct_read_source_path(project_root: Path, owner_path: str) -> Path:
    source_path = Path(owner_path)
    if source_path.is_absolute():
        return source_path
    parts = source_path.parts
    if len(parts) > 2 and parts[0] == "languages" and parts[1] == project_root.name:
        return project_root.joinpath(*parts[2:])
    return project_root / source_path


def _git_object_name(source_version: str, repo_relative_path: str) -> str:
    if source_version == "index":
        return f":{repo_relative_path}"
    if source_version == "head":
        return f"HEAD:{repo_relative_path}"
    raise ValueError(
        f"unknown query --source value: {source_version}; expected worktree, index, or head"
    )


def _git_output(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(cwd), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return result.stdout
    raise ValueError(f"git {' '.join(args)} failed in {cwd}: {result.stderr.strip()}")


def _direct_read_code_should_preserve_range(
    windows: list[dict[str, Any]],
    selector_range: tuple[int, int],
) -> bool:
    """Preserve exact code when a requested range starts before parser-owned items."""

    item_starts = [
        window["item_start"]
        for window in windows
        if isinstance(window.get("item_start"), int)
    ]
    return bool(item_starts) and selector_range[0] < min(item_starts)
