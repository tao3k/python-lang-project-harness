"""Compact and JSON renderers for Python semantic-search packets."""

from __future__ import annotations

import json
from typing import Any

from ._semantic_search_common import (
    escape_field_value,
    escape_scalar,
    render_fields,
    render_location,
)
from ._semantic_search_model import Fields
from .verification.facts import is_test_path


def render_python_semantic_search_packet_json(packet: dict[str, Any]) -> str:
    """Render a semantic-search packet as pretty JSON."""

    return json.dumps(packet, indent=2, sort_keys=False) + "\n"


def render_python_semantic_search_packet(packet: dict[str, Any]) -> str:
    """Render a compact line-oriented semantic-search packet."""

    if packet["renderMode"] == "seeds":
        return _render_seed_packet(packet)

    lines = [
        f"[{packet['header']['kind']}] {render_fields(packet['header']['fields'])}"
    ]
    owner_by_path = {owner["path"]: owner for owner in packet["owners"]}
    lines.extend(_package_lines(packet))
    lines.extend(_node_lines(packet))
    lines.extend(_owner_lines(packet))
    lines.extend(_hit_lines(packet, owner_by_path))
    if packet["view"] not in {"workspace", "prime"}:
        lines.extend(_edge_lines(packet))
    if packet["view"] not in {"workspace", "prime"}:
        lines.extend(_finding_lines(packet))
    lines.extend(_note_lines(packet))
    if packet["nextActions"]:
        rendered = ",".join(
            _render_next_action(action) for action in packet["nextActions"]
        )
        lines.append(f"|next {rendered}")
    return "\n".join(lines) + "\n"


def _package_lines(packet: dict[str, Any]) -> list[str]:
    return [
        f"|package {package['id']} {render_fields(package['fields'])}".rstrip()
        for package in packet.get("packages", [])
    ]


def _node_lines(packet: dict[str, Any]) -> list[str]:
    allowed = {"owner", "dependency", "test", "symbol", "package"}
    return [
        f"|{node['kind']} {node.get('path') or node['id']} {render_fields(node['fields'])}".rstrip()
        for node in packet["nodes"]
        if node["kind"] in allowed
    ]


def _owner_lines(packet: dict[str, Any]) -> list[str]:
    lines = []
    for owner in packet["owners"]:
        fields: Fields = {
            "role": owner["role"],
            "public": owner["public"],
            "exp": owner.get("exports", [])[:4],
            **owner["fields"],
        }
        owner_next = _render_owner_next_actions(
            owner["path"],
            owner.get("nextActions", []),
        )
        if owner_next:
            fields["next"] = owner_next
        lines.append(f"|owner {owner['path']} {render_fields(fields)}".rstrip())
    return lines


def _hit_lines(
    packet: dict[str, Any],
    owner_by_path: dict[str, dict[str, Any]],
) -> list[str]:
    lines = []
    for hit in packet["hits"]:
        owner_role = owner_by_path.get(hit["ownerPath"], {}).get("role")
        fields: Fields = {
            "owner": hit["ownerPath"],
            "kind": hit["kind"],
            "score": hit["score"],
            "reason": hit["reason"],
            **({"symbol": hit["symbol"]} if "symbol" in hit else {}),
            **_hit_evidence_fields(packet, owner_role, hit),
            **hit.get("fields", {}),
        }
        line_kind = "api" if hit["kind"] == "api" else "hit"
        lines.append(
            f"|{line_kind} {render_location(hit['location'])} {render_fields(fields)}".rstrip()
        )
    return lines


def _edge_lines(packet: dict[str, Any]) -> list[str]:
    lines = []
    for edge in packet["edges"]:
        fields = (
            f" {render_fields(edge.get('fields', {}))}" if edge.get("fields") else ""
        )
        lines.append(f"|edge {edge['from']} -{edge['kind']}-> {edge['to']}{fields}")
    return lines


def _finding_lines(packet: dict[str, Any]) -> list[str]:
    return [
        "|find "
        f"{finding['ruleId']} x{finding['count']} "
        f"at=O:{finding['location']['path']} severity={finding['severity']}"
        for finding in packet["findings"]
    ]


def _note_lines(packet: dict[str, Any]) -> list[str]:
    return [
        f"|note kind={note['kind']} message={escape_field_value(note['message'])}"
        for note in packet["notes"]
    ]


def _render_seed_packet(packet: dict[str, Any]) -> str:
    lines = [
        f"[{packet['header']['kind']}] {render_fields(packet['header']['fields'])}"
    ]
    lines.append(
        "|flow prime->owner|deps|symbol|tests pipe=text:owner,tests ingest=stdin"
    )
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
    for kind, values in groups.items():
        lines.append(f"|seed {kind}:{','.join(values)}")
    lines.extend(_note_lines(packet))
    return "\n".join(lines) + "\n"


def _add_seed(groups: dict[str, list[str]], kind: str, target: str) -> None:
    values = groups.setdefault(kind, [])
    if len(values) >= 8 or target in values:
        return
    values.append(target)


def _hit_evidence_fields(
    packet: dict[str, Any],
    owner_role: str | None,
    hit: dict[str, Any],
) -> Fields:
    if packet["view"] not in {"text", "ingest"}:
        return {}
    owner_path = hit["ownerPath"]
    fields: Fields = {"surface": "test" if is_test_path(owner_path) else "source"}
    if owner_role:
        fields["ownerRole"] = owner_role
    if hit.get("snippet"):
        fields["text"] = hit["snippet"]
    return fields


def _render_owner_next_actions(
    owner_path: str,
    actions: list[dict[str, Any]],
) -> list[str]:
    return [
        _render_next_action(action, context_owner_path=owner_path)
        for action in actions
        if action["kind"] != "owner" or action["target"] != owner_path
    ]


def _render_next_action(
    action: dict[str, Any],
    *,
    context_owner_path: str | None = None,
) -> str:
    suffix = ""
    if action.get("ownerPath") and action["ownerPath"] != context_owner_path:
        suffix = f"(owner={action['ownerPath']})"
    elif action.get("scope"):
        suffix = f"(scope={action['scope']})"
    return f"{action['kind']}:{escape_scalar(action['target'])}{suffix}"
