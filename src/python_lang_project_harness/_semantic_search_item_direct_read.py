"""Direct-source-read rendering for Python owner item selectors."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ._semantic_search_common import compact_fields, render_fields
from ._semantic_search_items import (
    _module_for_owner,
    _selector_line_range,
    _selector_range_items,
)

if TYPE_CHECKING:
    from ._project_policy_context import PythonHarnessReport


_MAX_EXACT_DIRECT_READ_LINES = 40


def owner_item_direct_read_lines(
    report: PythonHarnessReport,
    project_root: Path,
    owner_path: str,
    item_query: str,
    selector: str,
) -> str:
    """Return exact source windows for a hook direct-source-read selector."""

    del item_query
    selector_range = _selector_line_range(selector, owner_path)
    module = _module_for_owner(report, project_root, owner_path)
    if selector_range is None or module is None:
        raise ValueError(
            f"direct-source-read selector resolved to no parser-owned items: {owner_path}"
        )
    items = _selector_range_items(report, project_root, owner_path, selector_range)
    if not items:
        raise ValueError(
            f"direct-source-read selector resolved to no parser-owned items: {owner_path}"
        )
    windows = [
        _direct_read_item_window(module.source_lines, item, selector_range)
        for item in items
    ]
    outline_reason = _direct_read_outline_reason(selector_range, windows)
    if outline_reason is not None:
        return "\n".join(
            _direct_read_outline_lines(
                owner_path,
                selector,
                windows,
                outline_reason,
            )
        )
    lines = [
        f"[read-owner] q={owner_path} selector={json.dumps(selector)} window={len(items)}"
    ]
    for window in windows:
        lines.extend(_direct_read_item_lines(window))
    return "\n".join(lines)


def _direct_read_item_lines(
    window: dict[str, Any],
) -> list[str]:
    item = window["item"]
    start_line = window["start_line"]
    end_line = window["end_line"]
    text = window["text"]
    return [
        _direct_read_summary_line(item, start_line, end_line),
        _direct_read_code_line(item, start_line, end_line, text),
    ]


def _direct_read_item_window(
    source_lines: list[str],
    item: dict[str, Any],
    selector_range: tuple[int, int],
) -> dict[str, Any]:
    location = item.get("location", {})
    item_start, item_end = _item_line_range(location, selector_range)
    start_line = max(item_start, selector_range[0])
    end_line = min(item_end, selector_range[1])
    text = "\n".join(source_lines[start_line - 1 : end_line]).rstrip()
    return {
        "item": item,
        "requested_start": selector_range[0],
        "requested_end": selector_range[1],
        "item_start": item_start,
        "item_end": item_end,
        "start_line": start_line,
        "end_line": end_line,
        "text": text,
        "coverage": _direct_read_coverage(item_start, item_end, start_line, end_line),
        "low_signal": _is_low_signal_source_text(text),
    }


def _direct_read_outline_reason(
    selector_range: tuple[int, int],
    windows: list[dict[str, Any]],
) -> str | None:
    selector_line_count = selector_range[1] - selector_range[0] + 1
    if selector_line_count > _MAX_EXACT_DIRECT_READ_LINES:
        return "wide-selector"
    if windows and all(bool(window["low_signal"]) for window in windows):
        return "low-signal-window"
    return None


def _direct_read_outline_lines(
    owner_path: str,
    selector: str,
    windows: list[dict[str, Any]],
    reason: str,
) -> list[str]:
    lines = [
        "[read-plan] "
        + render_fields(
            compact_fields(
                {
                    "q": owner_path,
                    "selector": selector,
                    "mode": "range-outline",
                    "code": False,
                    "reason": reason,
                    "window": len(windows),
                }
            )
        )
    ]
    for window in windows:
        lines.append(_direct_read_range_line(window))
        lines.append(_direct_read_symbol_line(window))
    return lines


def _direct_read_range_line(window: dict[str, Any]) -> str:
    item = window["item"]
    return "|range " + render_fields(
        compact_fields(
            {
                "path": item.get("ownerPath"),
                "requested": f'{window["requested_start"]}:{window["requested_end"]}',
                "selected": f'{window["start_line"]}:{window["end_line"]}',
                "matched": f'{window["item_start"]}:{window["item_end"]}',
                "coverage": window["coverage"],
                "density": "low" if window["low_signal"] else "normal",
            }
        )
    )


def _direct_read_symbol_line(window: dict[str, Any]) -> str:
    item = window["item"]
    owner_path = item.get("ownerPath")
    line_range = f'{window["item_start"]}:{window["item_end"]}'
    return "|symbol " + render_fields(
        compact_fields(
            {
                "item": item.get("name"),
                "kind": item.get("kind"),
                "lineRange": line_range,
                "read": f"{owner_path}:{line_range}",
            }
        )
    )


def _direct_read_coverage(
    item_start: int,
    item_end: int,
    start_line: int,
    end_line: int,
) -> str:
    if start_line <= item_start and end_line >= item_end:
        return "full"
    if start_line > item_start and end_line >= item_end:
        return "tail-only"
    if start_line <= item_start and end_line < item_end:
        return "head-only"
    return "middle"


def _is_low_signal_source_text(text: str) -> bool:
    return not any(char.isalnum() or char == "_" for char in text)


def _item_line_range(
    location: dict[str, Any],
    selector_range: tuple[int, int],
) -> tuple[int, int]:
    line_range = _parse_line_range(location.get("lineRange"))
    if line_range is not None:
        return line_range
    item_start = int(location.get("line", selector_range[0]))
    return (item_start, item_start)


def _parse_line_range(value: object) -> tuple[int, int] | None:
    if not isinstance(value, str):
        return None
    start_text, separator, end_text = value.partition(":")
    if not separator:
        start_text, separator, end_text = value.partition("-")
    if not separator:
        return None
    try:
        start_line = int(start_text)
        end_line = int(end_text)
    except ValueError:
        return None
    if start_line < 1 or end_line < start_line:
        return None
    return (start_line, end_line)


def _direct_read_summary_line(
    item: dict[str, Any],
    start_line: int,
    end_line: int,
) -> str:
    return "|read " + render_fields(
        compact_fields(
            {'path': item.get('ownerPath'), 'item': item.get('name'), 'kind': item.get('kind'), 'lineRange': f'{start_line}:{end_line}', 'reason': 'direct-selector', 'truncated': False}
        )
    )


def _direct_read_code_line(
    item: dict[str, Any],
    start_line: int,
    end_line: int,
    text: str,
) -> str:
    return "|code " + render_fields(
        compact_fields(
            {'path': item.get('ownerPath'), 'lineRange': f'{start_line}:{end_line}', 'reason': 'direct-source-read', 'text': text}
        )
    )
