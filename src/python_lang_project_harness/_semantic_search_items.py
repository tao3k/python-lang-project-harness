"""Parser-owned compact item extraction for Python owner searches."""

from __future__ import annotations

import ast
import json
from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from . import _semantic_language_ids as ids
from ._semantic_search_common import compact_fields, display_path, render_fields
from ._semantic_search_model import MAX_OWNER_QUERY_ITEMS

if TYPE_CHECKING:
    from python_lang_parser import PythonModuleReport, PythonSymbol

    from ._model import PythonHarnessReport


def owner_item_query_payload(
    report: PythonHarnessReport,
    project_root: Path,
    owner_path: str,
    item_query: str | None,
) -> dict[str, Any]:
    """Return compact parser item facts for one owner path."""

    module = _module_for_owner(report, project_root, owner_path)
    if module is None:
        return {
            "items": [],
            "fields": {"item": 0, "itemStatus": "miss", "itemMatch": "none"},
            "notes": [{"kind": "owner-not-found", "message": owner_path}],
        }

    symbols = _sorted_symbols(module)
    terms = _query_terms(item_query)
    selected, match = _select_symbols(module, symbols, terms)
    fallback = False
    if not selected:
        selected = [symbol for symbol in symbols if symbol.is_top_level][
            :MAX_OWNER_QUERY_ITEMS
        ]
        match = "none" if terms else "top-items"
        fallback = bool(terms)

    items = [
        _item_record(module, project_root, owner_path, symbol)
        for symbol in selected[:MAX_OWNER_QUERY_ITEMS]
    ]
    fields: dict[str, object] = {
        "item": len(items),
        "itemQuery": item_query,
        "itemStatus": "hit" if items and not fallback else "miss",
        "itemMatch": match if items else "none",
        "fallback": "owner-top-items" if fallback and items else None,
    }
    return {
        "items": items,
        "fields": compact_fields(fields),
        "notes": []
        if items
        else [{"kind": "item-not-found", "message": item_query or owner_path}],
    }


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
    fields = payload["fields"]
    items = payload["items"]
    output_fields = compact_fields(
        {
            "q": owner_path,
            "pkg": ".",
            "own": 1,
            "item": len(items),
            "itemQuery": item_query,
            "output": "names" if names_only else None,
            "fallback": fields.get("fallback"),
        }
    )
    lines = [f"[search-owner] {render_fields(output_fields)}"]
    query_fields = compact_fields(
        {
            "itemQuery": item_query,
            "status": fields.get("itemStatus"),
            "match": fields.get("itemMatch"),
            "item": fields.get("item"),
            "reason": "parser-item-query",
            "output": "names" if names_only else None,
            "next": "code" if fields.get("item") else "revise-query",
        }
    )
    lines.append(f"|query {render_fields(query_fields)}")
    for item in items:
        item_fields = item.get("fields", {})
        location = item.get("location", {})
        lines.append(
            f"|item {item['name']} "
            + render_fields(
                compact_fields(
                    {
                        "kind": item.get("kind"),
                        "public": True if item_fields.get("public") is True else None,
                        "doc": True if item_fields.get("doc") is True else None,
                        "read": item_fields.get("read"),
                    }
                )
            )
        )
        code = item_fields.get("code")
        if names_only or not isinstance(code, str) or not code:
            continue
        lines.append(
            "|code "
            + render_fields(
                compact_fields(
                    {
                        "path": location.get("path"),
                        "startLine": location.get("line"),
                        "endLine": location.get("endLine"),
                        "reason": item_fields.get("reason"),
                        "truncated": item_fields.get("truncated"),
                        "text": code,
                    }
                )
            )
        )
    return "\n".join(lines)


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
    lines = [
        f"[read-owner] q={owner_path} selector={json.dumps(selector)} window={len(items)}"
    ]
    for item in items:
        location = item.get("location", {})
        item_start = int(location.get("line", selector_range[0]))
        item_end = int(location.get("endLine", item_start))
        start_line = max(item_start, selector_range[0])
        end_line = min(item_end, selector_range[1])
        text = "\n".join(module.source_lines[start_line - 1 : end_line]).rstrip()
        lines.append(
            "|read "
            + render_fields(
                compact_fields(
                    {
                        "path": owner_path,
                        "item": item.get("name"),
                        "kind": item.get("kind"),
                        "startLine": start_line,
                        "endLine": end_line,
                        "reason": "direct-selector",
                        "truncated": False,
                    }
                )
            )
        )
        lines.append(
            "|code "
            + render_fields(
                compact_fields(
                    {
                        "path": owner_path,
                        "startLine": start_line,
                        "endLine": end_line,
                        "reason": "direct-source-read",
                        "text": text,
                    }
                )
            )
        )
    return "\n".join(lines)


def owner_item_semantic_query_packet(
    report: PythonHarnessReport,
    project_root: Path,
    owner_path: str,
    item_query: str,
    *,
    output_mode: str,
    selector: str | None = None,
) -> dict[str, Any]:
    """Return a semantic-query-packet for owner-local Python item lookup."""

    payload = owner_item_query_payload(report, project_root, owner_path, item_query)
    items = payload["items"]
    fields = payload["fields"]
    selector_range = _selector_line_range(selector, owner_path)
    if selector_range is not None:
        items = _selector_range_items(report, project_root, owner_path, selector_range)
        fields = {
            **fields,
            "item": len(items),
            "itemStatus": "hit" if items else "miss",
            "itemMatch": "exact" if items else "none",
        }
    terms = _query_terms(item_query)
    return {
        "schemaId": ids.SEMANTIC_QUERY_PACKET_SCHEMA_ID,
        "schemaVersion": "1",
        "protocolId": ids.SEMANTIC_LANGUAGE_PROTOCOL_ID,
        "protocolVersion": ids.SEMANTIC_LANGUAGE_PROTOCOL_VERSION,
        "languageId": ids.PYTHON_LANGUAGE_ID,
        "providerId": ids.PYTHON_PROVIDER_ID,
        "binary": ids.PYTHON_BINARY,
        "namespace": ids.PYTHON_PROVIDER_NAMESPACE,
        "method": "query/owner-items",
        "projectRoot": str(project_root),
        "ownerPath": owner_path,
        "query": item_query,
        "queryTerms": terms,
        "matchMode": _query_match_mode(str(fields.get("itemMatch", "none"))),
        "outputMode": output_mode,
        "queryCoverage": [
            _query_coverage(term, items, str(fields.get("itemMatch", "none")))
            for term in terms
        ],
        "matches": [
            _semantic_query_match(item, include_code=output_mode != "names")
            for item in items
        ],
        "truncated": any(
            bool(item.get("fields", {}).get("truncated")) for item in items
        ),
        "notes": payload.get("notes", []),
    }


def _module_for_owner(
    report: PythonHarnessReport,
    project_root: Path,
    owner_path: str,
) -> PythonModuleReport | None:
    for module in report.modules:
        if (
            module.path is not None
            and display_path(module.path, project_root) == owner_path
        ):
            return module
    return None


def _selector_range_items(
    report: PythonHarnessReport,
    project_root: Path,
    owner_path: str,
    selector_range: tuple[int, int],
) -> list[dict[str, Any]]:
    module = _module_for_owner(report, project_root, owner_path)
    if module is None:
        return []
    return [
        _item_record(module, project_root, owner_path, symbol)
        for symbol in _sorted_symbols(module)
        if _symbol_overlaps_range(symbol, selector_range)
    ]


def _symbol_overlaps_range(
    symbol: PythonSymbol,
    selector_range: tuple[int, int],
) -> bool:
    start_line, end_line = selector_range
    symbol_end = symbol.end_line or symbol.location.line
    return symbol_end >= start_line and symbol.location.line <= end_line


def _selector_line_range(
    selector: str | None,
    owner_path: str,
) -> tuple[int, int] | None:
    if selector is None:
        return None
    normalized = selector.replace("\\", "/").removeprefix("owner:")
    if any(marker in normalized for marker in ("*", "{", "}")):
        return None
    path, separator, raw_range = normalized.rpartition(":")
    if not separator or path != owner_path:
        return None
    start_text, range_separator, end_text = raw_range.partition("-")
    try:
        start_line = int(start_text)
        end_line = int(end_text) if range_separator else start_line
    except ValueError:
        return None
    if start_line < 1 or end_line < 1:
        return None
    return (min(start_line, end_line), max(start_line, end_line))


def _query_match_mode(match: str) -> str:
    if match in {"exact", "fallback-contains"}:
        return match
    return "unknown"


def _query_coverage(
    term: str,
    items: list[dict[str, Any]],
    match: str,
) -> dict[str, Any]:
    exact_count = sum(1 for item in items if item.get("name") == term)
    if exact_count:
        return {
            "value": term,
            "status": "hit",
            "match": "exact",
            "matchCount": exact_count,
        }
    contains_count = sum(
        1 for item in items if term.casefold() in str(item.get("name", "")).casefold()
    )
    if contains_count and match == "fallback-contains":
        return {
            "value": term,
            "status": "hit",
            "match": "fallback-contains",
            "matchCount": contains_count,
        }
    return {
        "value": term,
        "status": "miss",
        "match": "none",
        "matchCount": 0,
        "nextAction": "query:broader-owner-item",
    }


def _semantic_query_match(
    item: dict[str, Any],
    *,
    include_code: bool,
) -> dict[str, Any]:
    fields = item.get("fields", {})
    location = item.get("location", {})
    match = {
        "name": item["name"],
        "kind": item["kind"],
        "visibility": "public" if fields.get("public") else "private",
        "doc": bool(fields.get("doc")),
        "location": {
            "path": location["path"],
            "line": location["line"],
            "endLine": location["endLine"],
            "column": location.get("column", 1),
        },
        "read": fields["read"],
        "truncated": bool(fields.get("truncated")),
        "fields": {
            "public": bool(fields.get("public")),
            "reason": str(fields.get("reason", "item-query")),
        },
    }
    code = fields.get("code")
    if include_code and isinstance(code, str):
        match["code"] = code
        match["projection"] = _semantic_query_projection(match, fields, code)
        match["outline"] = {
            "summary": f"{match['kind']} {match['name']}",
            "hotBlocks": [
                {
                    "label": match["name"],
                    "read": match["read"],
                    "reason": "parser-item-query",
                },
            ],
        }
    return match


def _semantic_query_projection(
    match: dict[str, Any],
    fields: dict[str, Any],
    code: str,
) -> dict[str, Any]:
    exact_read = str(match["read"])
    owner_path = str(match["location"]["path"])
    node_id = _projection_node_id(str(match["name"]))
    nodes = _semantic_outline_nodes(node_id, match, fields, code)
    return {
        "mode": "outline",
        "syntax": "semantic-outline",
        "sourceAuthority": "native-parser",
        "sourceFingerprint": _source_fingerprint(exact_read, code),
        "losslessStructure": True,
        "exactRead": exact_read,
        "nodes": nodes,
        "omitted": _semantic_outline_omissions(match, exact_read),
        "expandActions": _semantic_expand_actions(
            node_id,
            owner_path,
            exact_read,
            nodes,
        ),
    }


def _semantic_outline_nodes(
    root_id: str,
    match: dict[str, Any],
    fields: dict[str, Any],
    code: str,
) -> list[dict[str, Any]]:
    parser_nodes = fields.get("projectionNodes")
    if isinstance(parser_nodes, list) and parser_nodes:
        return _semantic_outline_parser_nodes(root_id, parser_nodes)
    exact_read = str(match["read"])
    nodes: list[dict[str, Any]] = []
    parent_stack: dict[int, str] = {0: root_id}
    for line in code.splitlines():
        label = line.strip()
        if not label:
            continue
        depth = max(0, _leading_spaces(line) // 2)
        node_index = len(nodes)
        node: dict[str, Any] = {
            "id": root_id if node_index == 0 else f"{root_id}:{node_index}",
            "kind": _outline_node_kind(label, node_index),
            "role": _outline_node_role(label, node_index),
            "label": label,
            "depth": depth,
            "read": exact_read,
        }
        if node_index > 0:
            node["parentId"] = _projection_parent_id(parent_stack, depth, root_id)
        flags = _outline_node_flags(label)
        if flags:
            node["flags"] = flags
        nodes.append(node)
        _projection_record_parent(parent_stack, depth, str(node["id"]))
    return nodes


def _semantic_outline_parser_nodes(
    root_id: str,
    parser_nodes: list[Any],
) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    parent_stack: dict[int, str] = {0: root_id}
    for parser_node in parser_nodes:
        if not isinstance(parser_node, dict):
            continue
        node_index = len(nodes)
        depth = int(parser_node.get("depth", 0))
        node = {
            "id": root_id if node_index == 0 else f"{root_id}:{node_index}",
            "kind": str(parser_node.get("kind", "statement")),
            "role": str(parser_node.get("role", "unknown")),
            "label": str(parser_node.get("label", "statement")),
            "depth": depth,
            "read": str(parser_node.get("read")),
        }
        if node_index > 0:
            node["parentId"] = _projection_parent_id(parent_stack, depth, root_id)
        flags = parser_node.get("flags")
        if isinstance(flags, list) and flags:
            node["flags"] = [str(flag) for flag in flags]
        nodes.append(node)
        _projection_record_parent(parent_stack, depth, str(node["id"]))
    return nodes


def _projection_parent_id(
    parent_stack: dict[int, str],
    depth: int,
    root_id: str,
) -> str:
    parent_depths = [stack_depth for stack_depth in parent_stack if stack_depth < depth]
    if not parent_depths:
        return root_id
    return parent_stack[max(parent_depths)]


def _projection_record_parent(
    parent_stack: dict[int, str],
    depth: int,
    node_id: str,
) -> None:
    for stored_depth in list(parent_stack):
        if stored_depth >= depth:
            del parent_stack[stored_depth]
    parent_stack[depth] = node_id


def _semantic_outline_omissions(
    match: dict[str, Any],
    exact_read: str,
) -> list[dict[str, Any]]:
    if not bool(match.get("truncated")):
        return []
    return [
        {
            "kind": "statement-tail",
            "reason": "outline projection capped a large item; expand exact read before editing",
            "read": exact_read,
        }
    ]


def _semantic_expand_actions(
    root_id: str,
    owner_path: str,
    exact_read: str,
    nodes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    actions = [
        {
            "kind": "exact-read",
            "target": root_id,
            "read": exact_read,
            "argv": [
                "py-harness",
                "query",
                "--from-hook",
                "direct-source-read",
                "--selector",
                exact_read,
                ".",
            ],
            "reason": "read exact source before editing",
        },
    ]
    seen_reads = {exact_read}
    for node in _hot_projection_nodes(nodes):
        read = str(node.get("read", ""))
        if not read or read in seen_reads:
            continue
        seen_reads.add(read)
        actions.append(
            {
                "kind": "exact-read",
                "target": str(node.get("id", root_id)),
                "read": read,
                "argv": [
                    "py-harness",
                    "query",
                    "--from-hook",
                    "direct-source-read",
                    "--selector",
                    read,
                    ".",
                ],
                "reason": f"expand {node.get('kind', 'statement')} node before editing",
            }
        )
        if len(actions) >= 8:
            break
    actions.append(
        {
            "kind": "owner-names",
            "target": owner_path,
            "argv": [
                "py-harness",
                "query",
                "--from-hook",
                "direct-source-read",
                "--selector",
                owner_path,
                ".",
            ],
            "reason": "return owner-local item names without code windows",
        }
    )
    return actions


def _hot_projection_nodes(
    nodes: list[dict[str, Any]],
) -> Iterable[dict[str, Any]]:
    return (node for node in nodes if _is_hot_projection_node(node))


def _is_hot_projection_node(node: dict[str, Any]) -> bool:
    return str(node.get("role", "")) in {
        "control-flow",
        "terminal",
        "call",
        "mutation",
        "effect",
    }


def _outline_node_kind(label: str, index: int) -> str:
    if index == 0:
        return "declaration"
    head = label.split(" ", 1)[0].rstrip(":")
    return head or "statement"


def _outline_node_role(label: str, index: int) -> str:
    if index == 0:
        return "declaration"
    if label.startswith(
        ("if ", "for ", "while ", "with ", "try:", "except ", "match ", "case ")
    ):
        return "control-flow"
    if label.startswith("call "):
        return "call"
    if label.startswith(("return", "raise", "break", "continue")):
        return "terminal"
    if label.startswith("await "):
        return "effect"
    if label.startswith("assign "):
        return "mutation"
    return "unknown"


def _outline_node_flags(label: str) -> list[str]:
    flags: list[str] = []
    if label.startswith(("if ", "match ", "case ")):
        flags.append("branch")
    if label.startswith(("for ", "while ")):
        flags.append("loop")
    if label.startswith("call "):
        flags.append("call")
    if label.startswith("return"):
        flags.append("return")
    if label.startswith("raise"):
        flags.append("raise")
    if label.startswith("break"):
        flags.append("break")
    if label.startswith("continue"):
        flags.append("continue")
    if "await " in label:
        flags.append("await")
    if label.startswith("assign "):
        flags.append("mutation")
    return flags


def _source_fingerprint(exact_read: str, code: str) -> str:
    return f"{exact_read}:{len(code)}:{_stable_hash(code)}"


def _stable_hash(value: str) -> str:
    current = 5381
    for char in value:
        current = ((current * 33) ^ ord(char)) & 0xFFFFFFFF
    return f"{current:x}"


def _projection_node_id(value: str) -> str:
    return "".join(char if char.isalnum() or char in "_.:-" else "_" for char in value)


def _sorted_symbols(module: PythonModuleReport) -> list[PythonSymbol]:
    return sorted(
        module.symbols,
        key=lambda symbol: (
            symbol.location.line,
            symbol.location.column,
            symbol.qualified_name,
        ),
    )


def _query_terms(item_query: str | None) -> list[str]:
    if item_query is None:
        return []
    return [term.strip() for term in item_query.split("|") if term.strip()]


def _select_symbols(
    module: PythonModuleReport,
    symbols: list[PythonSymbol],
    terms: list[str],
) -> tuple[list[PythonSymbol], str]:
    if not terms:
        return [symbol for symbol in symbols if symbol.is_top_level], "top-items"
    exact = _dedupe_symbols(
        symbol
        for term in terms
        for symbol in symbols
        if term in {symbol.name, symbol.qualified_name}
    )
    if exact:
        return exact, "exact"
    folded_terms = [term.casefold() for term in terms]
    contains = _dedupe_symbols(
        symbol
        for term in folded_terms
        for symbol in symbols
        if term in _symbol_query_text(module, symbol)
    )
    return contains, "fallback-contains" if contains else "none"


def _symbol_query_text(module: PythonModuleReport, symbol: PythonSymbol) -> str:
    end_line = symbol.end_line or symbol.location.line
    code, _, _ = _compact_code(
        module,
        str(symbol.location.path or ""),
        symbol.location.line,
        end_line,
    )
    return "\n".join((symbol.name, symbol.qualified_name, code)).casefold()


def _dedupe_symbols(symbols: Iterable[PythonSymbol]) -> list[PythonSymbol]:
    selected: list[PythonSymbol] = []
    seen: set[tuple[str, int, int]] = set()
    for symbol in symbols:
        key = (symbol.qualified_name, symbol.location.line, symbol.location.column)
        if key in seen:
            continue
        seen.add(key)
        selected.append(symbol)
    return selected


def _item_record(
    module: PythonModuleReport,
    project_root: Path,
    owner_path: str,
    symbol: PythonSymbol,
) -> dict[str, Any]:
    end_line = symbol.end_line or symbol.location.line
    code, truncated, projection_nodes = _compact_code(
        module,
        owner_path,
        symbol.location.line,
        end_line,
    )
    return {
        "name": symbol.qualified_name,
        "kind": symbol.kind.value,
        "ownerPath": owner_path,
        "location": {
            "path": owner_path,
            "line": symbol.location.line,
            "endLine": end_line,
            "column": max(1, symbol.location.column),
        },
        "fields": compact_fields(
            {
                "public": symbol.is_public,
                "doc": bool(symbol.docstring),
                "read": f"{owner_path}:{symbol.location.line}-{end_line}",
                "reason": "item-query",
                "truncated": truncated,
                "code": code,
                "projectionNodes": projection_nodes,
                "sourcePath": display_path(
                    symbol.location.path or owner_path, project_root
                ),
            }
        ),
    }


def _compact_code(
    module: PythonModuleReport,
    owner_path: str,
    start_line: int,
    end_line: int,
    *,
    max_lines: int = 80,
) -> tuple[str, bool, list[dict[str, Any]]]:
    raw_lines = module.source_lines[start_line - 1 : end_line]
    truncated = len(raw_lines) > max_lines
    selected_lines = raw_lines[:max_lines]
    return (
        _python_outline_projection(selected_lines),
        truncated,
        _python_projection_nodes(selected_lines, owner_path, start_line),
    )


def _python_outline_projection(raw_lines: list[str]) -> str:
    selected = [line.rstrip() for line in raw_lines if line.strip()]
    if not selected:
        return ""
    base_indent = min(_leading_spaces(line) for line in selected)
    source = "\n".join(
        line[base_indent:] if len(line) >= base_indent else line for line in raw_lines
    )
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return "\n".join(_trim_python_line(line, base_indent) for line in selected)
    lines: list[str] = []
    for node in tree.body:
        _append_python_outline(lines, node, depth=0)
    if lines:
        return "\n".join(line.rstrip() for line in lines if line.strip())
    return "\n".join(_trim_python_line(line, base_indent) for line in selected)


def _python_projection_nodes(
    raw_lines: list[str],
    owner_path: str,
    start_line: int,
) -> list[dict[str, Any]]:
    source = _dedented_python_source(raw_lines)
    if source is None:
        return []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    nodes: list[dict[str, Any]] = []
    for node in tree.body:
        _collect_python_projection_node(
            nodes,
            node,
            owner_path=owner_path,
            start_line=start_line,
            depth=0,
        )
    return nodes[:80]


def _dedented_python_source(raw_lines: list[str]) -> str | None:
    selected = [line.rstrip() for line in raw_lines if line.strip()]
    if not selected:
        return None
    base_indent = min(_leading_spaces(line) for line in selected)
    return "\n".join(
        line[base_indent:] if len(line) >= base_indent else line for line in raw_lines
    )


def _collect_python_projection_node(
    nodes: list[dict[str, Any]],
    node: ast.AST,
    *,
    owner_path: str,
    start_line: int,
    depth: int,
) -> None:
    label = _python_ast_node_label(node)
    if label is not None:
        nodes.append(
            {
                "kind": _outline_node_kind(label, len(nodes)),
                "role": _outline_node_role(label, len(nodes)),
                "label": label,
                "depth": depth,
                "read": _python_ast_node_read(owner_path, start_line, node),
                "flags": _outline_node_flags(label),
            }
        )
        for effect_node in _python_expression_effect_nodes(node):
            effect_label = _python_ast_node_label(effect_node)
            if effect_label is None:
                continue
            nodes.append(
                {
                    "kind": _outline_node_kind(effect_label, len(nodes)),
                    "role": _outline_node_role(effect_label, len(nodes)),
                    "label": effect_label,
                    "depth": depth + 1,
                    "read": _python_ast_node_read(owner_path, start_line, effect_node),
                    "flags": _outline_node_flags(effect_label),
                }
            )
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.stmt):
            _collect_python_projection_node(
                nodes,
                child,
                owner_path=owner_path,
                start_line=start_line,
                depth=depth + 1,
            )


def _python_ast_node_label(node: ast.AST) -> str | None:
    for labeler in (
        _python_declaration_label,
        _python_assignment_label,
        _python_control_label,
        _python_terminal_label,
    ):
        label = labeler(node)
        if label is not None:
            return label
    return None


def _python_expression_effect_nodes(node: ast.AST) -> Iterable[ast.AST]:
    if not isinstance(node, ast.Expr | ast.Assign | ast.AnnAssign | ast.Return):
        return ()
    return tuple(child for child in ast.walk(node) if isinstance(child, ast.Await))


def _python_declaration_label(node: ast.AST) -> str | None:
    if isinstance(node, ast.ClassDef):
        return f"class {node.name}"
    if isinstance(node, ast.AsyncFunctionDef):
        return f"async def {node.name}"
    if isinstance(node, ast.FunctionDef):
        return f"def {node.name}"
    return None


def _python_assignment_label(node: ast.AST) -> str | None:
    if isinstance(node, ast.Assign):
        return f"assign {_targets(node.targets)}"
    if isinstance(node, ast.AnnAssign):
        return f"assign {_expr(node.target)}"
    return None


def _python_control_label(node: ast.AST) -> str | None:
    if isinstance(node, ast.If):
        return f"if {_expr(node.test)}"
    if isinstance(node, ast.For | ast.AsyncFor):
        return f"for {_expr(node.target)} in {_expr(node.iter)}"
    if isinstance(node, ast.While):
        return f"while {_expr(node.test)}"
    if isinstance(node, ast.With | ast.AsyncWith):
        return f"with {_with_items(node.items)}"
    if isinstance(node, ast.Try):
        return "try:"
    if isinstance(node, ast.Match):
        return f"match {_expr(node.subject)}"
    return None


def _python_terminal_label(node: ast.AST) -> str | None:
    if isinstance(node, ast.Return):
        return f"return {_expr(node.value)}"
    if isinstance(node, ast.Raise):
        return f"raise {_expr(node.exc)}"
    if isinstance(node, ast.Break):
        return "break"
    if isinstance(node, ast.Continue):
        return "continue"
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
        return f"call {_expr(node.value)}"
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Await):
        return f"await {_expr(node.value.value)}"
    if isinstance(node, ast.Await):
        return f"await {_expr(node.value)}"
    return None


def _python_ast_node_read(owner_path: str, start_line: int, node: ast.AST) -> str:
    line = getattr(node, "lineno", 1)
    end_line = getattr(node, "end_lineno", line) or line
    absolute_start = start_line + line - 1
    absolute_end = start_line + end_line - 1
    return f"{owner_path}:{absolute_start}-{absolute_end}"


def _append_python_outline(
    lines: list[str],
    node: ast.AST,
    *,
    depth: int,
) -> None:
    prefix = "  " * depth
    for append in (
        _append_declaration_outline,
        _append_assignment_outline,
        _append_control_flow_outline,
        _append_terminal_outline,
    ):
        if append(lines, node, prefix=prefix, depth=depth):
            return
    lines.append(f"{prefix}{node.__class__.__name__}")


def _append_declaration_outline(
    lines: list[str],
    node: ast.AST,
    *,
    prefix: str,
    depth: int,
) -> bool:
    if isinstance(node, ast.ClassDef):
        bases = ", ".join(_expr(base) for base in node.bases)
        suffix = f"({bases})" if bases else ""
        lines.append(f"{prefix}class {node.name}{suffix}:")
        _append_python_block(lines, node.body, depth=depth + 1)
        return True
    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
        async_prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
        returns = f" -> {_expr(node.returns)}" if node.returns is not None else ""
        lines.append(
            f"{prefix}{async_prefix}def {node.name}({_args(node.args)}){returns}:"
        )
        _append_python_block(lines, node.body, depth=depth + 1)
        return True
    return False


def _append_assignment_outline(
    lines: list[str],
    node: ast.AST,
    *,
    prefix: str,
    depth: int,
) -> bool:
    del depth
    if isinstance(node, ast.Assign):
        lines.append(f"{prefix}assign {_targets(node.targets)} = {_expr(node.value)}")
        return True
    if isinstance(node, ast.AnnAssign):
        target = _expr(node.target)
        annotation = _expr(node.annotation)
        value = f" = {_expr(node.value)}" if node.value is not None else ""
        lines.append(f"{prefix}assign {target}: {annotation}{value}")
        return True
    if isinstance(node, ast.Import | ast.ImportFrom):
        lines.append(f"{prefix}{_import_stmt(node)}")
        return True
    return False


def _append_control_flow_outline(
    lines: list[str],
    node: ast.AST,
    *,
    prefix: str,
    depth: int,
) -> bool:
    if isinstance(node, ast.If):
        _append_if_outline(lines, node, prefix=prefix, depth=depth)
        return True
    if isinstance(node, ast.For | ast.AsyncFor):
        async_prefix = "async " if isinstance(node, ast.AsyncFor) else ""
        lines.append(
            f"{prefix}{async_prefix}for {_expr(node.target)} in {_expr(node.iter)}:"
        )
        _append_python_block(lines, node.body, depth=depth + 1)
        return True
    if isinstance(node, ast.While):
        lines.append(f"{prefix}while {_expr(node.test)}:")
        _append_python_block(lines, node.body, depth=depth + 1)
        return True
    if isinstance(node, ast.With | ast.AsyncWith):
        async_prefix = "async " if isinstance(node, ast.AsyncWith) else ""
        lines.append(f"{prefix}{async_prefix}with {_with_items(node.items)}:")
        _append_python_block(lines, node.body, depth=depth + 1)
        return True
    return _append_exception_or_match_outline(lines, node, prefix=prefix, depth=depth)


def _append_if_outline(
    lines: list[str],
    node: ast.If,
    *,
    prefix: str,
    depth: int,
) -> None:
    lines.append(f"{prefix}if {_expr(node.test)}:")
    _append_python_block(lines, node.body, depth=depth + 1)
    if node.orelse:
        lines.append(f"{prefix}else:")
        _append_python_block(lines, node.orelse, depth=depth + 1)


def _append_exception_or_match_outline(
    lines: list[str],
    node: ast.AST,
    *,
    prefix: str,
    depth: int,
) -> bool:
    if isinstance(node, ast.Try):
        lines.append(f"{prefix}try:")
        _append_python_block(lines, node.body, depth=depth + 1)
        for handler in node.handlers:
            label = _expr(handler.type) if handler.type is not None else "Exception"
            lines.append(f"{prefix}except {label}:")
            _append_python_block(lines, handler.body, depth=depth + 1)
        if node.finalbody:
            lines.append(f"{prefix}finally:")
            _append_python_block(lines, node.finalbody, depth=depth + 1)
        return True
    if isinstance(node, ast.Match):
        lines.append(f"{prefix}match {_expr(node.subject)}:")
        for case in node.cases:
            guard = f" if {_expr(case.guard)}" if case.guard is not None else ""
            lines.append(f"{prefix}  case {_expr(case.pattern)}{guard}:")
            _append_python_block(lines, case.body, depth=depth + 2)
        return True
    return False


def _append_terminal_outline(
    lines: list[str],
    node: ast.AST,
    *,
    prefix: str,
    depth: int,
) -> bool:
    del depth
    if isinstance(node, ast.Return):
        lines.append(f"{prefix}return {_expr(node.value)}")
        return True
    if isinstance(node, ast.Raise):
        lines.append(f"{prefix}raise {_expr(node.exc)}")
        return True
    if isinstance(node, ast.Break):
        lines.append(f"{prefix}break")
        return True
    if isinstance(node, ast.Continue):
        lines.append(f"{prefix}continue")
        return True
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Await):
        lines.append(f"{prefix}await {_expr(node.value.value)}")
        return True
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
        lines.append(f"{prefix}call {_expr(node.value)}")
        return True
    if isinstance(node, ast.Pass):
        lines.append(f"{prefix}pass")
        return True
    return False


def _append_python_block(
    lines: list[str],
    body: list[ast.stmt],
    *,
    depth: int,
    max_nodes: int = 24,
) -> None:
    for node in body[:max_nodes]:
        _append_python_outline(lines, node, depth=depth)
    if len(body) > max_nodes:
        lines.append(f"{'  ' * depth}... {len(body) - max_nodes} more statements")


def _leading_spaces(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _trim_python_line(line: str, base_indent: int) -> str:
    trimmed = line[base_indent:] if len(line) >= base_indent else line
    return trimmed.strip()


def _args(args: ast.arguments) -> str:
    return _expr(args)


def _targets(targets: list[ast.expr]) -> str:
    return ", ".join(_expr(target) for target in targets)


def _with_items(items: list[ast.withitem]) -> str:
    rendered: list[str] = []
    for item in items:
        optional = (
            f" as {_expr(item.optional_vars)}" if item.optional_vars is not None else ""
        )
        rendered.append(f"{_expr(item.context_expr)}{optional}")
    return ", ".join(rendered)


def _import_stmt(node: ast.Import | ast.ImportFrom) -> str:
    if isinstance(node, ast.Import):
        return "import " + ", ".join(alias.name for alias in node.names)
    module = "." * node.level + (node.module or "")
    return f"from {module} import " + ", ".join(alias.name for alias in node.names)


def _expr(node: ast.AST | None) -> str:
    if node is None:
        return ""
    try:
        text = ast.unparse(node)
    except Exception:
        text = node.__class__.__name__
    return _limit_expr(" ".join(text.split()))


def _limit_expr(text: str, *, max_chars: int = 120) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "..."
