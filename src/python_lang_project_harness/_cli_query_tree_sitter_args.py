"""Tree-sitter query argument helpers for the Python CLI."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def is_tree_sitter_query_state(state: Any) -> bool:
    return state.catalog is not None or state.tree_sitter_query is not None


def tree_sitter_query_args_error(state: Any) -> str | None:
    if state.catalog is not None and state.tree_sitter_query is not None:
        return "query accepts only one of --catalog or --treesitter-query"
    if state.from_hook is not None:
        return "query --catalog/--treesitter-query cannot be combined with --from-hook"
    if len(state.positionals) > 1:
        return "expected optional PROJECT_ROOT for tree-sitter query"
    if state.names_only:
        return "--names-only cannot be combined with --catalog or --treesitter-query"
    if state.json_output and state.code_only:
        return "--code cannot be combined with --json"
    if state.surfaces:
        return "query --surface requires broad --from-hook direct-source-read --selector and --term"
    if state.render_mode is not None:
        return "query --view requires broad hook search or exact direct-source-read read-packet"
    return None


def tree_sitter_query_protocol_args(args_type: type[Any], state: Any) -> Any:
    return args_type(
        "query",
        selector=state.selector,
        catalog=state.catalog,
        tree_sitter_query=state.tree_sitter_query,
        query_set=tuple(state.terms),
        project_root=None if not state.positionals else Path(state.positionals[0]),
        package_path=state.package_path,
        json=state.json_output,
        code_only=state.code_only,
    )
