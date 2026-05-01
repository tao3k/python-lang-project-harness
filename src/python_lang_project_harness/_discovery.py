"""Python project path discovery for embedded harness runs."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ._constants import IGNORED_DIR_NAMES
from ._model import PythonProjectHarnessScope
from ._project_metadata import read_python_project_metadata

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence


def discover_python_files(
    paths: Sequence[str | Path],
    *,
    ignored_dir_names: Iterable[str] | None = None,
) -> tuple[Path, ...]:
    """Discover Python files below the provided paths."""

    ignored_names = (
        IGNORED_DIR_NAMES if ignored_dir_names is None else frozenset(ignored_dir_names)
    )
    discovered: list[Path] = []
    seen: set[Path] = set()
    for raw_path in paths:
        path = Path(raw_path)
        if path.is_file():
            if path.suffix == ".py":
                _append_unique_path(discovered, seen, path)
            continue
        if path.is_dir():
            for candidate in path.rglob("*.py"):
                if is_scannable_python_file(
                    candidate,
                    ignored_dir_names=ignored_names,
                ):
                    _append_unique_path(discovered, seen, candidate)
    return tuple(sorted(discovered, key=lambda item: item.as_posix()))


def python_project_harness_paths(
    project_root: str | Path,
    *,
    include_tests: bool = True,
    source_dir_names: Sequence[str] = ("src",),
    test_dir_names: Sequence[str] = ("tests",),
    extra_path_names: Sequence[str] = (),
) -> tuple[Path, ...]:
    """Return project scan paths for embedded pytest harness checks."""

    return python_project_harness_scope(
        project_root,
        include_tests=include_tests,
        source_dir_names=source_dir_names,
        test_dir_names=test_dir_names,
        extra_path_names=extra_path_names,
    ).monitored_paths


def python_project_harness_scope(
    project_root: str | Path,
    *,
    include_tests: bool = True,
    source_dir_names: Sequence[str] = ("src",),
    test_dir_names: Sequence[str] = ("tests",),
    extra_path_names: Sequence[str] = (),
) -> PythonProjectHarnessScope:
    """Return the default project-wide monitoring scope."""

    root = Path(project_root)
    source_paths = tuple(
        root / name for name in source_dir_names if (root / name).exists()
    )
    test_paths = tuple(root / name for name in test_dir_names if (root / name).exists())
    extra_paths = tuple(
        (root / name).resolve() for name in extra_path_names if (root / name).exists()
    )
    metadata = read_python_project_metadata(root)
    metadata_package_roots = () if metadata is None else metadata.package_roots
    project_paths = _project_scan_paths(
        root,
        include_tests=include_tests,
        test_dir_names=test_dir_names,
        metadata_package_roots=metadata_package_roots,
    )
    return PythonProjectHarnessScope(
        project_root=root,
        project_paths=project_paths,
        source_paths=source_paths,
        test_paths=test_paths,
        extra_paths=extra_paths,
        include_tests=include_tests,
    )


def _project_scan_paths(
    root: Path,
    *,
    include_tests: bool,
    test_dir_names: Sequence[str],
    metadata_package_roots: tuple[Path, ...],
) -> tuple[Path, ...]:
    external_package_roots = _external_package_roots(root, metadata_package_roots)
    if include_tests:
        return _dedupe_paths((root, *external_package_roots))

    excluded_test_dir_names = {
        name for name in test_dir_names if (root / name).is_dir()
    }
    candidates = [
        child
        for child in sorted(root.iterdir(), key=lambda path: path.as_posix())
        if child.name not in excluded_test_dir_names
        and child.name not in IGNORED_DIR_NAMES
        and (child.suffix == ".py" or child.is_dir())
    ]
    return _dedupe_paths((*candidates, *external_package_roots))


def is_scannable_python_file(
    path: Path,
    *,
    ignored_dir_names: frozenset[str],
) -> bool:
    """Return whether a Python file belongs to the harness-owned scan scope."""

    return not any(part in ignored_dir_names for part in path.parts)


def _append_unique_path(discovered: list[Path], seen: set[Path], path: Path) -> None:
    key = path.resolve()
    if key in seen:
        return
    seen.add(key)
    discovered.append(path)


def _external_package_roots(
    root: Path,
    package_roots: tuple[Path, ...],
) -> tuple[Path, ...]:
    return tuple(
        package_root
        for package_root in package_roots
        if not _is_relative_to(package_root, root)
    )


def _dedupe_paths(paths: Iterable[Path]) -> tuple[Path, ...]:
    seen: set[Path] = set()
    deduped: list[Path] = []
    for path in paths:
        key = path.resolve()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(path)
    return tuple(deduped)


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True
