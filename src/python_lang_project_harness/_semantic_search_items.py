"""Parser-owned compact item extraction for Python owner searches."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from . import _semantic_language_ids as ids
from ._python_compact import compact_python_item
from ._semantic_projection import semantic_query_projection
from ._semantic_search_common import compact_fields, display_path
from ._semantic_search_import_routes import import_definition_routes
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
    import_routes = (
        import_definition_routes(report, project_root, module, terms)
        if terms and match != "exact"
        else []
    )
    fallback = False
    if import_routes:
        selected = []
        match = "candidate"
    elif not selected:
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
        "itemMatch": match if items or import_routes else "none",
        "fallback": "owner-top-items" if fallback and items else None,
        "next": _import_route_next(import_routes[0]) if import_routes else None,
    }
    return {
        "items": items,
        "fields": compact_fields(fields),
        "notes": _item_query_notes(item_query, owner_path, items, import_routes),
        "importRoutes": import_routes,
    }


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
    import_routes = payload.get("importRoutes", [])
    selector_range = _selector_line_range(selector, owner_path)
    if selector_range is not None:
        items = _selector_range_items(report, project_root, owner_path, selector_range)
        fields = {
            **fields,
            "item": len(items),
            "itemStatus": "hit" if items else "miss",
            "itemMatch": "exact" if items else "none",
        }
        import_routes = []
    terms = _query_terms(item_query)
    from ._semantic_syntax_refs import (
        annotate_python_owner_item_syntax_refs,
        attach_python_syntax_refs,
    )

    syntax_refs = annotate_python_owner_item_syntax_refs(items)
    packet = {
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
        "patchSafety": {
            "level": "read-safe",
            "reason": "compact query packet is not a mutation authority",
            "nextAction": "query --from-hook direct-source-read",
        },
        "queryCoverage": [
            _query_coverage(
                term,
                items,
                str(fields.get("itemMatch", "none")),
                import_routes if isinstance(import_routes, list) else [],
            )
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
    attach_python_syntax_refs(packet, syntax_refs)
    return packet


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
    path_and_start, separator, end_text = normalized.rpartition(":")
    if not separator:
        return None
    path, separator, start_text = path_and_start.rpartition(":")
    if separator and path == owner_path:
        pass
    elif path_and_start == owner_path:
        start_text, separator, end_text = end_text.partition("-")
        if not separator:
            return None
    else:
        return None
    try:
        start_line = int(start_text)
        end_line = int(end_text)
    except ValueError:
        return None
    if start_line < 1 or end_line < 1:
        return None
    return (min(start_line, end_line), max(start_line, end_line))


def _query_match_mode(match: str) -> str:
    if match in {"exact", "fallback-contains", "candidate"}:
        return match
    return "unknown"


def _query_coverage(
    term: str,
    items: list[dict[str, Any]],
    match: str,
    import_routes: list[Any],
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
    candidate_routes = _routes_for_term(import_routes, term)
    if candidate_routes:
        return {
            "value": term,
            "status": "partial",
            "match": "candidate",
            "matchCount": len(candidate_routes),
            "candidateNames": [
                f"{route['ownerPath']}::{route['query']}" for route in candidate_routes
            ],
            "nextAction": _import_route_next(candidate_routes[0]),
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
        "location": {"path": location["path"], "lineRange": location["lineRange"]},
        "read": fields["read"],
        "patchSafety": {
            "level": "read-safe",
            "reason": "read exact source locator before editing this compact match",
            "exactRead": fields["read"],
        },
        "truncated": bool(fields.get("truncated")),
        "fields": {
            "public": bool(fields.get("public")),
            "reason": str(fields.get("reason", "item-query")),
        },
    }
    for syntax_key in ("syntaxQueryRef", "syntaxMatchRef", "syntaxCaptureRef"):
        syntax_value = fields.get(syntax_key)
        if isinstance(syntax_value, str):
            match["fields"][syntax_key] = syntax_value
    code = fields.get("code")
    if include_code and isinstance(code, str):
        match["code"] = code
        projection = semantic_query_projection(match, fields, code)
        projected_code = _projected_code_from_rows(projection)
        if projected_code:
            match["code"] = projected_code
        match["projection"] = projection
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


def _projected_code_from_rows(projection: dict[str, Any]) -> str:
    rows = projection.get("renderedRows")
    if not isinstance(rows, list):
        return ""
    texts = [
        str(row.get("text", ""))
        for row in rows
        if isinstance(row, dict) and str(row.get("text", "")).strip()
    ]
    return "\n".join(texts)


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


def _item_query_notes(
    item_query: str | None,
    owner_path: str,
    items: list[dict[str, Any]],
    import_routes: list[dict[str, str]],
) -> list[dict[str, str]]:
    if import_routes:
        route = import_routes[0]
        return [
            {
                "kind": "imported-definition",
                "message": (
                    f"{item_query or owner_path} is imported in {owner_path}; "
                    f"next={_import_route_next(route)}"
                ),
            }
        ]
    if items:
        return []
    return [{"kind": "item-not-found", "message": item_query or owner_path}]


def _routes_for_term(
    import_routes: list[Any],
    term: str,
) -> list[dict[str, str]]:
    return [
        route
        for route in import_routes
        if isinstance(route, dict) and route.get("term") == term
    ]


def _import_route_next(route: dict[str, str]) -> str:
    return f"py-harness query {route['ownerPath']} --term {route['query']} --code ."


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
            "lineRange": f"{symbol.location.line}:{end_line}",
        },
        "fields": compact_fields(
            {
                "public": symbol.is_public,
                "doc": bool(symbol.docstring),
                "read": f"{owner_path}:{symbol.location.line}:{end_line}",
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
    compact = compact_python_item(raw_lines, owner_path, start_line)
    if compact.projection_nodes:
        return compact.code, False, compact.projection_nodes

    truncated = len(raw_lines) > max_lines
    selected_lines = raw_lines[:max_lines]
    compact = compact_python_item(selected_lines, owner_path, start_line)
    return compact.code, truncated, compact.projection_nodes
