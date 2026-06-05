"""Query command argument parsing for the Python harness CLI."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ._cli_query_arg_consume import (
    ProtocolArgError,
    QueryParseState,
    consume_query_arg,
)
from ._cli_query_hook_args import (
    is_broad_hook_query,
    owner_path_from_query_selector,
    selector_has_line_range,
)
from ._cli_query_tree_sitter_args import (
    is_tree_sitter_query_state,
    tree_sitter_query_args_error,
    tree_sitter_query_protocol_args,
)

if TYPE_CHECKING:
    from ._cli_args import ProtocolArgs


def parse_query_args(
    args_type: type[ProtocolArgs],
    args: list[str] | tuple[str, ...],
) -> ProtocolArgs:
    """Parse py-harness query arguments into protocol args."""

    if args and args[0] in {"--help", "-h"}:
        return args_type("help")
    state = QueryParseState()
    index = 0
    while index < len(args):
        index = consume_query_arg(state, args, index)
        if isinstance(index, ProtocolArgError):
            return args_type("error", error=index.message)
    return _query_args_result(args_type, state)


def _query_args_result(
    args_type: type[ProtocolArgs],
    state: QueryParseState,
) -> ProtocolArgs:
    error = _query_args_error(state)
    if error is not None:
        return args_type("error", error=error)
    if is_broad_hook_query(state.from_hook, state.selector, state.terms):
        return args_type(
            "search",
            view="fzf",
            query=",".join(state.terms),
            query_set=tuple(state.terms),
            project_root=_query_project_root(state),
            package_path=state.package_path,
            pipes=tuple(state.surfaces),
            render_mode=state.render_mode,
        )
    if is_tree_sitter_query_state(state):
        return tree_sitter_query_protocol_args(args_type, state)
    owner_path = (
        owner_path_from_query_selector(state.selector)
        if state.selector is not None
        else state.positionals[0]
    )
    return args_type(
        "query",
        owner_path=owner_path,
        selector=state.selector,
        query_set=tuple(state.terms),
        project_root=_query_project_root(state),
        package_path=state.package_path,
        json=state.json_output,
        names_only=_query_names_only(state),
        code_only=state.code_only,
        render_mode=state.render_mode,
    )


def _query_args_error(state: QueryParseState) -> str | None:
    if state.from_hook is not None and state.from_hook != "direct-source-read":
        return f"unsupported query hook route: {state.from_hook}"
    if is_tree_sitter_query_state(state):
        return tree_sitter_query_args_error(state)
    if not state.selector and not state.positionals:
        return "query requires an owner path"
    if len(state.positionals) > (2 if state.selector is None else 1):
        return "expected owner path and optional PROJECT_ROOT"
    if not state.terms and state.from_hook != "direct-source-read":
        return "query requires at least one --term"
    broad_hook_query = is_broad_hook_query(state.from_hook, state.selector, state.terms)
    exact_read_packet = bool(
        state.from_hook == "direct-source-read"
        and state.json_output
        and state.render_mode == "read-packet"
        and selector_has_line_range(state.selector)
    )
    if state.json_output and state.code_only and not exact_read_packet:
        return "--code cannot be combined with --json"
    if state.names_only and state.code_only:
        return "--code cannot be combined with --names-only"
    if state.surfaces and not broad_hook_query:
        return "query --surface requires broad --from-hook direct-source-read --selector and --term"
    if state.render_mode is not None and not (broad_hook_query or exact_read_packet):
        return "query --view requires broad hook search or exact direct-source-read read-packet"
    return None


def _query_project_root(state: QueryParseState) -> Path | None:
    if state.selector is None:
        return None if len(state.positionals) == 1 else Path(state.positionals[1])
    return None if not state.positionals else Path(state.positionals[0])


def _query_names_only(state: QueryParseState) -> bool:
    if state.names_only:
        return True
    return bool(
        not state.terms
        and state.from_hook == "direct-source-read"
        and not state.code_only
        and not state.json_output
        and not selector_has_line_range(state.selector)
    )
