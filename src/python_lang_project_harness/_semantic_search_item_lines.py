"""Line rendering for Python owner item query results."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from ._semantic_search_common import compact_fields, render_fields
from ._semantic_search_items import owner_item_query_payload

if TYPE_CHECKING:
    from ._project_policy_context import PythonHarnessReport


def owner_item_query_lines(
    report: PythonHarnessReport,
    project_root: Path,
    owner_path: str,
    item_query: str,
    *,
    names_only: bool = False,
) -> str:
    """Render compact owner item query lines for the top-level query command."""

    payload = owner_item_query_payload(report, project_root, owner_path, item_query)
    lines = [_header_line(owner_path, item_query, payload, names_only)]
    lines.append(_query_line(item_query, payload, names_only))
    lines.extend(_note_lines(payload))
    lines.extend(_item_lines(payload["items"], names_only))
    return "\n".join(lines)


def _header_line(
    owner_path: str,
    item_query: str,
    payload: dict[str, Any],
    names_only: bool,
) -> str:
    fields = payload["fields"]
    output_fields = compact_fields(
        {
            "q": owner_path,
            "pkg": ".",
            "own": 1,
            "item": len(payload["items"]),
            "itemQuery": item_query,
            "output": "names" if names_only else None,
            "fallback": fields.get("fallback"),
        }
    )
    return f"[search-owner] {render_fields(output_fields)}"


def _query_line(
    item_query: str,
    payload: dict[str, Any],
    names_only: bool,
) -> str:
    fields = payload["fields"]
    query_fields = compact_fields(
        {
            "itemQuery": item_query,
            "status": fields.get("itemStatus"),
            "match": fields.get("itemMatch"),
            "item": fields.get("item"),
            "reason": "parser-item-query",
            "output": "names" if names_only else None,
            "next": fields.get("next")
            or ("code" if fields.get("item") else "revise-query"),
        }
    )
    return f"|query {render_fields(query_fields)}"


def _note_lines(payload: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for note in payload.get("notes", []):
        if not isinstance(note, dict):
            continue
        lines.append(
            "|note "
            + render_fields(
                compact_fields(
                    {
                        "kind": note.get("kind"),
                        "message": note.get("message"),
                    }
                )
            )
        )
    return lines


def _item_lines(items: list[dict[str, Any]], names_only: bool) -> list[str]:
    lines: list[str] = []
    for item in items:
        lines.append(_item_summary_line(item))
        code_line = _item_code_line(item, names_only)
        if code_line is not None:
            lines.append(code_line)
    return lines


def _item_summary_line(item: dict[str, Any]) -> str:
    item_fields = item.get("fields", {})
    return f"|item {item['name']} " + render_fields(
        compact_fields(
            {
                "kind": item.get("kind"),
                "public": True if item_fields.get("public") is True else None,
                "doc": True if item_fields.get("doc") is True else None,
                "read": item_fields.get("read"),
            }
        )
    )


def _item_code_line(item: dict[str, Any], names_only: bool) -> str | None:
    item_fields = item.get("fields", {})
    location = item.get("location", {})
    code = item_fields.get("code")
    if names_only or not isinstance(code, str) or not code:
        return None
    return "|code " + render_fields(
        compact_fields(
            {'path': location.get('path'), 'lineRange': location.get('lineRange'), 'reason': 'item-query', 'truncated': False, 'text': code}
        )
    )
