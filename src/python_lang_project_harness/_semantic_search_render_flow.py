"""Flow, note, and synthesis renderers for semantic-search packets."""

from __future__ import annotations

from typing import Any

from ._semantic_search_common import escape_field_value, escape_scalar, render_fields
from ._semantic_search_render_lines import query_coverage_lines, render_next_action


def finding_lines(packet: dict[str, Any]) -> list[str]:
    return [
        "|find "
        f"{finding['ruleId']} x{finding['count']} "
        f"at=O:{finding['location']['path']} severity={finding['severity']}"
        for finding in packet["findings"]
    ]


def note_lines(packet: dict[str, Any]) -> list[str]:
    return [
        f"|note kind={note['kind']} message={escape_field_value(note['message'])}"
        for note in packet["notes"]
    ]


def synthesis_lines(packet: dict[str, Any]) -> list[str]:
    synthesis = packet.get("searchSynthesis")
    if not synthesis:
        return []
    lines = [
        f"|synthesis summary={escape_field_value(synthesis.get('summary', ''))}".rstrip()
    ]
    seeds = synthesis.get("seeds", [])
    if seeds:
        lines.append(f"|seed {','.join(render_next_action(seed) for seed in seeds)}")
    return lines


def avoid_next_action_lines(packet: dict[str, Any]) -> list[str]:
    return [
        f"|avoid {render_next_action(action)} reason={escape_scalar(action['reason'])}"
        for action in packet.get("avoidNextActions", [])
    ]


def seed_packet_text(packet: dict[str, Any]) -> str:
    lines = [
        f"[{packet['header']['kind']}] {render_fields(packet['header']['fields'])}"
    ]
    lines.append(
        "|flow prime->owner|deps|symbol|tests pipe=text:owner,tests ingest=stdin"
    )
    lines.extend(query_coverage_lines(packet))
    lines.extend(_seed_lines(packet))
    lines.extend(note_lines(packet))
    lines.extend(synthesis_lines(packet))
    lines.extend(avoid_next_action_lines(packet))
    return "\n".join(lines) + "\n"


def _seed_lines(packet: dict[str, Any]) -> list[str]:
    groups = _seed_groups(packet)
    return [f"|seed {kind}:{','.join(values)}" for kind, values in groups.items()]


def _seed_groups(packet: dict[str, Any]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for owner in packet["owners"]:
        _add_seed(groups, "owner", owner["path"])
        for export_name in owner.get("exports", [])[:4]:
            _add_seed(groups, "symbol", export_name)
    for hit in packet["hits"]:
        _add_seed(groups, "owner", hit["ownerPath"])
        if "symbol" in hit:
            _add_seed(groups, "symbol", hit["symbol"])
    for action in packet["nextActions"]:
        _add_seed(groups, action["kind"], action["target"])
    return groups


def _add_seed(groups: dict[str, list[str]], kind: str, target: str) -> None:
    values = groups.setdefault(kind, [])
    if len(values) >= 8 or target in values:
        return
    values.append(target)
