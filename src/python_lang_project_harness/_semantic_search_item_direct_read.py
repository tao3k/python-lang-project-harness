"""Direct-source-read rendering for Python owner item selectors."""

from __future__ import annotations

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
) -> str:
    """Return exact source windows for a hook direct-source-read selector."""

    del item_query
    source_lines, selector_range, windows = _direct_read_windows(
        report, project_root, owner_path, selector
    )
    return render_direct_read_windows(
        owner_path=owner_path,
        selector=selector,
        source_lines=source_lines,
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
) -> dict[str, Any]:
    """Return the structured read packet for a direct-source-read selector."""

    del item_query
    _source_lines, selector_range, windows = _direct_read_windows(
        report, project_root, owner_path, selector
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
    )
    attach_python_syntax_refs(packet, syntax_refs)
    return packet


def _direct_read_windows(
    report: PythonHarnessReport,
    project_root: Path,
    owner_path: str,
    selector: str,
) -> tuple[list[str], tuple[int, int], list[dict[str, Any]]]:
    selector_range = _selector_line_range(selector, owner_path)
    module = _module_for_owner(report, project_root, owner_path)
    if selector_range is None or module is None:
        raise ValueError(
            f"direct-source-read selector resolved to no parser-owned source: {owner_path}"
        )
    if selector_range[0] > len(module.source_lines):
        raise ValueError(
            f"direct-source-read selector is outside owner source: {owner_path}"
        )
    items = _selector_range_items(report, project_root, owner_path, selector_range)
    if items:
        windows = [
            direct_read_item_window(module.source_lines, item, selector_range)
            for item in items
        ]
    else:
        windows = [
            direct_read_range_window(module.source_lines, owner_path, selector_range)
        ]
    return module.source_lines, selector_range, windows
