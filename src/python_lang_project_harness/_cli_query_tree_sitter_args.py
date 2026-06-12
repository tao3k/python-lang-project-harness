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
    if state.workspace_root is not None and state.positionals:
        return (
            "query accepts either --workspace <workspace-root> or one positional "
            "WORKSPACE, not both"
        )
    if len(state.positionals) > 1:
        return "query accepts at most one positional WORKSPACE"
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
        asp_syntax_query_captures=tuple(state.asp_syntax_query_captures),
        asp_syntax_query_node_types=tuple(state.asp_syntax_query_node_types),
        asp_syntax_query_fields=tuple(state.asp_syntax_query_fields),
        asp_syntax_query_predicates=tuple(state.asp_syntax_query_predicates),
        query_set=tuple(state.terms),
        project_root=_tree_sitter_query_project_root(state),
        package_path=state.package_path,
        workspace=state.workspace or bool(state.positionals),
        json=state.json_output,
        code_only=state.code_only,
    )


def _tree_sitter_query_project_root(state: Any) -> Path | None:
    if state.workspace_root is not None:
        return state.workspace_root
    if len(state.positionals) == 1:
        return Path(state.positionals[0])
    return None
