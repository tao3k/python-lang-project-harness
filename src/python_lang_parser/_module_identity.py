"""Python module identity helpers derived from import-root path shape."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


def python_module_name_from_path(path: str | Path) -> str:
    """Return the leaf Python module name for a source path."""

    return Path(path).stem


def python_module_namespace_parts(
    path: str | Path,
    *,
    import_roots: Sequence[str | Path] = (),
    project_root: str | Path | None = None,
) -> tuple[str, ...]:
    """Return import-style module namespace parts for a Python source path."""

    source_path = Path(path)
    relative = _relative_to_first_import_root(source_path, import_roots)
    if relative is None and project_root is not None:
        relative = _try_relative_to(source_path, Path(project_root))
    if relative is None:
        relative = source_path
    if relative == Path("."):
        relative = Path(source_path.name)
    module_path = relative.with_suffix("")
    parts = module_path.parts
    if parts and parts[-1] == "__init__":
        return parts[:-1]
    return parts


def python_module_is_package_init(path: str | Path) -> bool:
    """Return whether a source path represents a package `__init__.py` module."""

    return Path(path).name == "__init__.py"


def _relative_to_first_import_root(
    path: Path,
    import_roots: Sequence[str | Path],
) -> Path | None:
    for root in import_roots:
        relative = _try_relative_to(path, Path(root))
        if relative is not None:
            return relative
    return None


def _try_relative_to(path: Path, root: Path) -> Path | None:
    try:
        return path.relative_to(root)
    except ValueError:
        return None
