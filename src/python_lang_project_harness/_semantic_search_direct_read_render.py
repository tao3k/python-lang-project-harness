"""Rendering helpers for exact direct-source-read source windows."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_MAX_EXACT_DIRECT_READ_LINES = 32


def render_direct_read_windows(
    *,
    owner_path: str,
    selector: str,
    source_lines: list[str],
    selector_range: tuple[int, int],
    windows: list[dict[str, Any]],
    code_only: bool,
) -> str:
    if code_only:
        return "\n\n".join(
            _direct_read_code_only_text(source_lines, window) for window in windows
        ).rstrip()
    outline_reason = _direct_read_outline_reason(selector_range, windows)
    if outline_reason is not None:
        return "\n".join(
            _direct_read_outline_lines(owner_path, selector, windows, outline_reason)
        )
    lines = [
        f"[read-owner] q={owner_path} selector={json.dumps(selector)} window={len(windows)}"
    ]
    for window in windows:
        lines.extend(_direct_read_item_lines(window))
    return "\n".join(lines)


def render_direct_read_packet(
    *,
    project_root: Path,
    owner_path: str,
    selector: str,
    selector_range: tuple[int, int],
    windows: list[dict[str, Any]],
    source_version: str,
    repository_root: str | None = None,
    git_blob_oid: str | None = None,
) -> dict[str, Any]:
    """Return the structured read packet for an exact direct-source-read."""

    packet: dict[str, Any] = {
        "schemaId": "agent.semantic-protocols.semantic-read-packet",
        "schemaVersion": "1",
        "protocolId": "agent.semantic-protocols.semantic-language",
        "protocolVersion": "1",
        "languageId": "python",
        "providerId": "py-harness",
        "binary": "py-harness",
        "namespace": "agent.semantic-protocols.languages.python.py-harness",
        "method": "query/direct-source-read",
        "projectRoot": str(project_root),
        "sourceVersion": source_version,
        "ownerPath": owner_path,
        "selector": selector,
        "fromHook": "direct-source-read",
        "outputMode": "read-packet",
        "truncated": False,
        "notes": [],
    }
    if repository_root is not None:
        packet["repositoryRoot"] = repository_root
    if git_blob_oid is not None:
        packet["gitBlobOid"] = git_blob_oid
    outline_reason = _direct_read_outline_reason(selector_range, windows)
    if outline_reason is None:
        packet["sourceWindows"] = [
            _direct_read_source_window(window) for window in windows
        ]
    else:
        packet["readPlan"] = _direct_read_read_plan(windows, outline_reason)
    return packet


def direct_read_item_window(
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


def direct_read_range_window(
    source_lines: list[str],
    owner_path: str,
    selector_range: tuple[int, int],
) -> dict[str, Any]:
    """Build a source-preserved fallback window when no parser item owns the range."""

    start_line = selector_range[0]
    end_line = min(selector_range[1], len(source_lines))
    text = "\n".join(source_lines[start_line - 1 : end_line]).rstrip()
    return {
        "item": {
            "ownerPath": owner_path,
            "location": {"lineRange": f"{start_line}:{end_line}"},
        },
        "requested_start": selector_range[0],
        "requested_end": selector_range[1],
        "item_start": start_line,
        "item_end": end_line,
        "start_line": start_line,
        "end_line": end_line,
        "text": text,
        "coverage": _direct_read_coverage(start_line, end_line, start_line, end_line),
        "low_signal": _is_low_signal_source_text(text),
    }


def _direct_read_code_text(source_lines: list[str], window: dict[str, Any]) -> str:
    if window["low_signal"]:
        return source_lines[window["item_start"] - 1].rstrip()
    return str(window["text"])


def _direct_read_code_only_text(source_lines: list[str], window: dict[str, Any]) -> str:
    if window["coverage"] == "full":
        return str(window["text"])
    fields = window["item"].get("fields", {})
    code = fields.get("code") if isinstance(fields, dict) else None
    if isinstance(code, str) and code.strip():
        return code.rstrip()
    return _direct_read_code_text(source_lines, window)


def _direct_read_item_lines(window: dict[str, Any]) -> list[str]:
    item = window["item"]
    start_line = window["start_line"]
    end_line = window["end_line"]
    return [
        _direct_read_summary_line(item, start_line, end_line),
    ]


def _direct_read_outline_reason(
    selector_range: tuple[int, int],
    windows: list[dict[str, Any]],
) -> str | None:
    if windows and all(bool(window["low_signal"]) for window in windows):
        return "low-signal-window"
    return None


def _direct_read_outline_lines(
    owner_path: str,
    selector: str,
    windows: list[dict[str, Any]],
    reason: str,
) -> list[str]:
    frontier = ",".join(
        f"{_read_plan_symbol_id(index)}.code" for index, _window in enumerate(windows)
    )
    lines = [
        "[read-plan] "
        + _render_fields(
            _compact_fields(
                {
                    "q": owner_path,
                    "selector": selector,
                    "mode": "range-frontier",
                    "code": False,
                    "reason": reason,
                    "maxWindow": _MAX_EXACT_DIRECT_READ_LINES,
                    "alg": "symbol-frontier",
                    "frontier": frontier,
                    "avoid": "repeat-wide-read,manual-window-scan,raw-read",
                }
            )
        )
    ]
    for window in windows:
        lines.append(_direct_read_range_line(window))
        lines.append(_direct_read_symbol_line(window))
    return lines


def _direct_read_range_line(window: dict[str, Any]) -> str:
    return "|range " + _render_fields(
        _compact_fields(
            {
                "path": window["item"].get("ownerPath", ""),
                "requested": f"{window['requested_start']}:{window['requested_end']}",
                "selected": f"{window['item_start']}:{window['item_end']}",
                "matched": f"{window['start_line']}:{window['end_line']}",
                "coverage": window["coverage"],
                "density": "low" if window["low_signal"] else "normal",
            }
        )
    )


def _direct_read_symbol_line(window: dict[str, Any]) -> str:
    item = window["item"]
    reason = "parser-item" if item.get("name") else "selector-range"
    return "|symbol " + _render_fields(
        _compact_fields(
            {
                "item": item.get("name", ""),
                "kind": item.get("kind", ""),
                "lineRange": f"{window['item_start']}:{window['item_end']}",
                "read": f"{item.get('ownerPath', '')}:{window['item_start']}:{window['item_end']}",
                "reason": reason,
            }
        )
    )


def _read_plan_symbol_id(index: int) -> str:
    return "S" if index == 0 else f"S{index + 1}"


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
    stripped_lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not stripped_lines:
        return True
    if not any(char.isalnum() or char == "_" for char in text):
        return True
    return all(line.startswith(("'", '"', "]", ")", "}")) for line in stripped_lines)


def _item_line_range(
    location: dict[str, Any],
    selector_range: tuple[int, int],
) -> tuple[int, int]:
    line_range = location.get("lineRange")
    if isinstance(line_range, str):
        start_text, separator, end_text = line_range.partition(":")
        if separator:
            try:
                return (int(start_text), int(end_text))
            except ValueError:
                pass
    start_line = location.get("startLine")
    end_line = location.get("endLine")
    if isinstance(start_line, int) and isinstance(end_line, int):
        return (start_line, end_line)
    return selector_range


def _direct_read_summary_line(
    item: dict[str, Any], start_line: int, end_line: int
) -> str:
    return "|read " + _render_fields(
        _compact_fields(
            {
                "path": item.get("ownerPath", ""),
                "item": item.get("name", ""),
                "kind": item.get("kind", ""),
                "lineRange": f"{start_line}:{end_line}",
                "read": f"{item.get('ownerPath', '')}:{start_line}:{end_line}",
                "next": "direct-source-read",
                "reason": "direct-selector",
                "truncated": False,
            }
        )
    )


def _direct_read_source_window(window: dict[str, Any]) -> dict[str, Any]:
    item = window["item"]
    start_line = int(window["start_line"])
    end_line = int(window["end_line"])
    text = str(window["text"])
    source_window: dict[str, Any] = {
        "ownerPath": item.get("ownerPath", ""),
        "location": {
            "path": item.get("ownerPath", ""),
            "startLine": start_line,
            "endLine": end_line,
            "lineRange": f"{start_line}:{end_line}",
        },
        "read": f"{item.get('ownerPath', '')}:{start_line}:{end_line}",
        "lineCount": max(0, end_line - start_line + 1),
        "reason": "direct-selector",
        "text": text,
        "lines": [
            {"number": start_line + index, "text": line}
            for index, line in enumerate(text.splitlines())
        ],
        "truncated": False,
    }
    if item.get("name"):
        source_window["itemName"] = item["name"]
    if item.get("kind"):
        source_window["itemKind"] = item["kind"]
    return source_window


def _direct_read_read_plan(
    windows: list[dict[str, Any]],
    reason: str,
) -> dict[str, Any]:
    symbols = [
        _direct_read_plan_symbol(window)
        for window in windows
        if window["item"].get("name") and window["item"].get("kind")
    ]
    plan: dict[str, Any] = {
        "mode": "range-frontier",
        "code": False,
        "reason": reason,
        "maxWindowLines": _MAX_EXACT_DIRECT_READ_LINES,
        "algorithm": "symbol-frontier",
        "frontier": [
            _direct_read_plan_frontier(window, index)
            for index, window in enumerate(windows)
        ],
        "avoid": ["repeat-wide-read", "manual-window-scan", "raw-read"],
        "omit": ["code"],
        "ranges": [_direct_read_plan_range(window) for window in windows],
    }
    if symbols:
        plan["symbols"] = symbols
    return plan


def _direct_read_plan_range(window: dict[str, Any]) -> dict[str, Any]:
    return {
        "path": window["item"].get("ownerPath", ""),
        "requested": f"{window['requested_start']}:{window['requested_end']}",
        "selected": f"{window['item_start']}:{window['item_end']}",
        "matched": f"{window['start_line']}:{window['end_line']}",
        "coverage": window["coverage"],
        "density": "low" if window["low_signal"] else "normal",
    }


def _direct_read_plan_frontier(
    window: dict[str, Any],
    index: int,
) -> dict[str, Any]:
    item = window["item"]
    item_name = item.get("name")
    item_kind = item.get("kind")
    symbol_id = _read_plan_symbol_id(index)
    read = f"{item.get('ownerPath', '')}:{window['item_start']}:{window['item_end']}"
    if item_name and item_kind:
        return {
            "id": symbol_id,
            "kind": "symbol",
            "target": f"{item.get('ownerPath', '')}@{window['item_start']}:{window['item_end']}",
            "read": read,
            "action": "code",
            "rank": index + 1,
            "reason": "parser-item",
        }
    return {
        "id": symbol_id,
        "kind": "range",
        "target": f"{item.get('ownerPath', '')}@{window['item_start']}:{window['item_end']}",
        "action": "outline",
        "rank": index + 1,
        "reason": "selector-range",
    }


def _direct_read_plan_symbol(window: dict[str, Any]) -> dict[str, Any]:
    item = window["item"]
    return {
        "itemName": item["name"],
        "itemKind": item["kind"],
        "lineRange": f"{window['item_start']}:{window['item_end']}",
        "read": f"{item.get('ownerPath', '')}:{window['item_start']}:{window['item_end']}",
    }


def _compact_fields(fields: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in fields.items()
        if value is not None and value != "" and value != []
    }


def _render_fields(fields: dict[str, Any]) -> str:
    return " ".join(
        f"{key}={_render_field_value(value)}" for key, value in fields.items()
    )


def _render_field_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, tuple)):
        return ",".join(_render_field_value(item) for item in value)
    if isinstance(value, str):
        if any(char.isspace() for char in value) or any(
            char in value for char in ('"', "=")
        ):
            return json.dumps(value)
        return value
    return str(value)
