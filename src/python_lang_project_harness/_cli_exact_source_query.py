"""Exact selector source query path that does not require project-wide facts."""

from __future__ import annotations

import tokenize
from pathlib import Path

from ._cli_args import ProtocolArgs
from ._semantic_search_direct_read_render import (
    direct_read_item_window,
    render_direct_read_windows,
)
from ._semantic_search_item_direct_read_ast import ast_selector_range_items


def render_exact_source_query_code(
    args: ProtocolArgs, project_root: Path
) -> str | None:
    """Render exact selector code without running the full project harness."""

    if not _supports_exact_source_query_code(args):
        return None
    selector = args.selector
    if selector is None:
        return None
    owner_path, line_range = _selector_owner_and_line_range(selector)
    if owner_path is None:
        return None
    source_lines = _read_source_lines(project_root, owner_path)
    if line_range is None:
        return _render_full_selector_file(source_lines, args)
    return _render_selector_line_range(source_lines, owner_path, line_range, args)


def _read_source_lines(project_root: Path, owner_path: str) -> list[str]:
    source_path = _source_path(project_root, owner_path)
    try:
        with tokenize.open(source_path) as handle:
            return handle.read().splitlines()
    except OSError as error:
        raise ValueError(
            f"query selector source could not be read: {source_path}"
        ) from error


def _render_full_selector_file(
    source_lines: list[str],
    args: ProtocolArgs,
) -> str | None:
    if args.query_set:
        return None
    return "\n".join(source_lines).rstrip() + "\n"


def _render_selector_line_range(
    source_lines: list[str],
    owner_path: str,
    line_range: tuple[int, int],
    args: ProtocolArgs,
) -> str | None:
    start_line, end_line = line_range
    if start_line > len(source_lines):
        raise ValueError(f"query selector is outside source: {owner_path}")
    end_line = min(end_line, len(source_lines))
    ast_items = ast_selector_range_items(
        source_lines, owner_path, (start_line, end_line)
    )
    if ast_items and start_line >= _first_item_start_line(ast_items):
        windows = [
            direct_read_item_window(source_lines, item, (start_line, end_line))
            for item in ast_items
        ]
        rendered = render_direct_read_windows(
            owner_path=owner_path,
            selector=args.selector or owner_path,
            source_lines=source_lines,
            selector_range=(start_line, end_line),
            windows=windows,
            code_only=True,
        )
        if rendered:
            return rendered + "\n"
    return "\n".join(source_lines[start_line - 1 : end_line]).rstrip() + "\n"


def _first_item_start_line(items: list[dict[str, object]]) -> int:
    starts = [
        _item_start_line(item) for item in items if _item_start_line(item) is not None
    ]
    return min(starts) if starts else 1


def _item_start_line(item: dict[str, object]) -> int | None:
    location = item.get("location")
    if not isinstance(location, dict):
        return None
    line_range = location.get("lineRange")
    if not isinstance(line_range, str):
        return None
    start_text, _separator, _end_text = line_range.partition(":")
    try:
        return int(start_text)
    except ValueError:
        return None


def _supports_exact_source_query_code(args: ProtocolArgs) -> bool:
    return (
        args.command == "query"
        and args.selector is not None
        and args.code_only
        and not args.json
        and not args.names_only
        and args.catalog is None
        and args.tree_sitter_query is None
        and args.source_version == "worktree"
        and args.render_mode is None
    )


def _selector_owner_and_line_range(
    selector: str,
) -> tuple[str | None, tuple[int, int] | None]:
    normalized = selector.replace("\\", "/").removeprefix("owner:")
    if any(marker in normalized for marker in ("*", "{", "}")):
        return None, None
    path_text, separator, line_range_text = normalized.rpartition(":")
    if not separator:
        return normalized or None, None
    start_text, separator, end_text = line_range_text.partition("-")
    if not separator:
        return None, None
    try:
        start_line = int(start_text)
        end_line = int(end_text)
    except ValueError:
        return None, None
    if start_line < 1 or end_line < start_line:
        return None, None
    return path_text or None, (start_line, end_line)


def _source_path(project_root: Path, owner_path: str) -> Path:
    source_path = Path(owner_path)
    if source_path.is_absolute():
        return source_path
    parts = source_path.parts
    if len(parts) > 2 and parts[0] == "languages" and parts[1] == project_root.name:
        return project_root.joinpath(*parts[2:])
    return project_root / source_path
