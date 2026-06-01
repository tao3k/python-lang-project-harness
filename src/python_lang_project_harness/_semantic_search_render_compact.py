"""Compact text rendering orchestration for Python search packets."""

from __future__ import annotations

from typing import Any

from ._semantic_search_common import compact_fields, render_fields
from ._semantic_search_render_flow import (
    avoid_next_action_lines,
    finding_lines,
    note_lines,
    seed_packet_text,
    synthesis_lines,
)
from ._semantic_search_render_lines import (
    edge_lines,
    hit_lines,
    node_lines,
    owner_lines,
    package_lines,
    query_coverage_lines,
    render_next_action,
)


def render_compact_packet(packet: dict[str, Any]) -> str:
    if packet["renderMode"] == "seeds":
        return seed_packet_text(packet)
    return "\n".join(_compact_packet_lines(packet)) + "\n"


def _compact_packet_lines(packet: dict[str, Any]) -> list[str]:
    owner_by_path = {owner["path"]: owner for owner in packet["owners"]}
    lines = [
        f"[{packet['header']['kind']}] {render_fields(packet['header']['fields'])}"
    ]
    _extend_payload_lines(packet, owner_by_path, lines)
    _extend_flow_lines(packet, lines)
    return lines


def _extend_payload_lines(
    packet: dict[str, Any],
    owner_by_path: dict[str, dict[str, Any]],
    lines: list[str],
) -> None:
    lines.extend(query_coverage_lines(packet))
    lines.extend(package_lines(packet))
    lines.extend(node_lines(packet))
    lines.extend(owner_lines(packet))
    lines.extend(hit_lines(packet, owner_by_path))
    if packet["view"] not in {"workspace", "prime"}:
        lines.extend(edge_lines(packet))
        lines.extend(finding_lines(packet))


def _extend_flow_lines(packet: dict[str, Any], lines: list[str]) -> None:
    lines.extend(note_lines(packet))
    lines.extend(runtime_cost_lines(packet))
    lines.extend(synthesis_lines(packet))
    lines.extend(avoid_next_action_lines(packet))
    lines.extend(
        f"|next {','.join(render_next_action(action) for action in packet['nextActions'])}"
        for _ in [None]
        if packet["nextActions"]
    )


def runtime_cost_lines(packet: dict[str, Any]) -> list[str]:
    runtime_cost = packet.get("runtimeCost")
    if not isinstance(runtime_cost, dict):
        return []
    fields = compact_fields(
        {
            "cache": runtime_cost.get("cacheStatus"),
            "elapsedMs": runtime_cost.get("elapsedMs"),
            "parseMs": runtime_cost.get("parseMs"),
            "sourceFiles": runtime_cost.get("sourceFilesParsed"),
            "packages": runtime_cost.get("packagesScanned"),
            "reused": runtime_cost.get("parserFactsReused"),
            **runtime_cost.get("fields", {}),
            "reason": runtime_cost.get("reason"),
        }
    )
    return [f"|runtime {render_fields(fields)}"]
