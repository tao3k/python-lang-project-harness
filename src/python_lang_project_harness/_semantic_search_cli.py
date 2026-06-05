"""CLI parsing helpers for Python semantic-search commands."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ._semantic_language import python_semantic_search_view_descriptor


@dataclass(slots=True)
class ParsedSemanticSearchArgs:
    view: str | None = None
    query: str | None = None
    item_query: str | None = None
    project_root: Path | None = None
    package_path: Path | None = None
    owner_path: str | None = None
    query_set: tuple[str, ...] = ()
    pipes: tuple[str, ...] = ()
    json: bool = False
    code_only: bool = False
    render_mode: str | None = None
    error: str | None = None


@dataclass(slots=True)
class _SearchOptionState:
    positionals: list[str] = field(default_factory=list)
    query_set: list[str] = field(default_factory=list)
    item_query: str | None = None
    json: bool = False
    code_only: bool = False
    render_mode: str | None = None
    package_path: Path | None = None
    owner_path: str | None = None


@dataclass(slots=True)
class _ConsumedOption:
    advance: int = 1
    error: str | None = None


def parse_semantic_search_args(
    args: list[str] | tuple[str, ...],
) -> ParsedSemanticSearchArgs:
    view = args[0] if args else None
    if view is None or view in {"--help", "-h"}:
        return ParsedSemanticSearchArgs(
            error=(
                "usage: py-harness search "
                "<workspace|prime|owner|dependency|deps|api|public-external-types|policy|symbol|callsite|import|tests|fzf|text|ingest> "
                "... [--json] [--code] [--package PATH] [PROJECT_ROOT]"
            ),
        )
    descriptor = python_semantic_search_view_descriptor(view)
    if descriptor is None:
        return ParsedSemanticSearchArgs(error=f"unknown search view: {view}")

    state, error = _parse_search_option_state(view, args[1:])
    if error is not None:
        return ParsedSemanticSearchArgs(error=error)
    if state.query_set and not _search_view_supports_query_set(view):
        return ParsedSemanticSearchArgs(
            error=f"search {view} does not support --query-set"
        )
    if state.item_query is not None and view != "owner":
        return ParsedSemanticSearchArgs(
            error="--query is only supported by search owner items",
        )
    if state.code_only and state.json:
        return ParsedSemanticSearchArgs(error="--code cannot be combined with --json")
    if state.code_only and not (view == "owner" and state.item_query is not None):
        return ParsedSemanticSearchArgs(
            error="--code requires search owner <path> items --query <symbol>",
        )
    if state.owner_path is not None and not (view == "fzf" and state.query_set):
        return ParsedSemanticSearchArgs(
            error="--owner is only supported by search fzf --query-set",
        )
    if descriptor["requiresQuery"]:
        return _required_query_args(view, descriptor, state)
    return _project_only_args(view, state)


def _parse_search_option_state(
    view: str,
    args: list[str] | tuple[str, ...],
) -> tuple[_SearchOptionState, str | None]:
    state = _SearchOptionState()
    index = 0
    while index < len(args):
        consumed = _consume_search_option(view, args, index, state)
        if consumed.error is not None:
            return state, consumed.error
        index += consumed.advance
    return state, None


def _consume_search_option(
    view: str,
    args: list[str] | tuple[str, ...],
    index: int,
    state: _SearchOptionState,
) -> _ConsumedOption:
    arg = args[index]
    if _is_flag_like_literal_search_query(
        view, state.positionals, state.query_set, arg
    ):
        state.positionals.append(arg)
        return _ConsumedOption()

    match arg:
        case "--json":
            state.json = True
        case "--code":
            state.code_only = True
        case "--view":
            value = _optional_arg(args, index + 1)
            if value not in {"graph", "hits", "both", "seeds"}:
                return _ConsumedOption(
                    error="--view requires graph, hits, both, or seeds",
                )
            state.render_mode = value
            return _ConsumedOption(advance=2)
        case "--package":
            value = _optional_arg(args, index + 1)
            if value is None:
                return _ConsumedOption(error="--package requires a package path")
            state.package_path = Path(value)
            return _ConsumedOption(advance=2)
        case "--owner":
            value = _literal_arg(args, index + 1)
            if value is None:
                return _ConsumedOption(error="--owner requires an owner path")
            state.owner_path = value
            return _ConsumedOption(advance=2)
        case "--query-set":
            value = _literal_arg(args, index + 1)
            if value is None:
                return _ConsumedOption(error="--query-set requires a query term")
            state.query_set.append(value)
            return _ConsumedOption(advance=2)
        case "--query":
            value = _literal_arg(args, index + 1)
            if value is None:
                return _ConsumedOption(error="--query requires an item query")
            state.item_query = value
            return _ConsumedOption(advance=2)
        case _ if arg.startswith("-"):
            return _ConsumedOption(error=f"unknown search option: {arg}")
        case _:
            state.positionals.append(arg)
    return _ConsumedOption()


def _required_query_args(
    view: str,
    descriptor: dict[str, object],
    state: _SearchOptionState,
) -> ParsedSemanticSearchArgs:
    query = (
        ",".join(state.query_set)
        if state.query_set
        else (state.positionals[0] if state.positionals else None)
    )
    if query is None:
        return ParsedSemanticSearchArgs(error=f"search {view} requires a query")

    accepted_pipes = descriptor.get("acceptedPipes", ())
    pipes, project_root, error = _parse_search_pipe_positionals(
        state.positionals if state.query_set else state.positionals[1:],
        accepted_pipes if isinstance(accepted_pipes, tuple | list) else (),
    )
    if error is not None:
        return ParsedSemanticSearchArgs(error=error)
    return ParsedSemanticSearchArgs(
        view=view,
        query=query,
        item_query=state.item_query,
        owner_path=state.owner_path,
        query_set=tuple(state.query_set),
        project_root=None if project_root is None else Path(project_root),
        package_path=state.package_path,
        pipes=tuple(pipes),
        json=state.json,
        code_only=state.code_only,
        render_mode=state.render_mode,
    )


def _project_only_args(
    view: str,
    state: _SearchOptionState,
) -> ParsedSemanticSearchArgs:
    if len(state.positionals) > 1:
        return ParsedSemanticSearchArgs(
            error="expected at most one PROJECT_ROOT argument"
        )
    return ParsedSemanticSearchArgs(
        view=view,
        project_root=None if not state.positionals else Path(state.positionals[0]),
        package_path=state.package_path,
        json=state.json,
        code_only=state.code_only,
        render_mode=state.render_mode,
    )


def _parse_search_pipe_positionals(
    positionals: list[str],
    accepted_pipes: list[str] | tuple[str, ...],
) -> tuple[list[str], str | None, str | None]:
    pipes: list[str] = []
    index = 0
    while index < len(positionals) and index < len(accepted_pipes):
        if positionals[index] != accepted_pipes[index]:
            break
        pipes.append(positionals[index])
        index += 1
    remaining = positionals[index:]
    if len(remaining) > 1:
        if not accepted_pipes:
            return pipes, remaining[0], "expected at most one PROJECT_ROOT argument"
        return (
            pipes,
            remaining[0],
            f"expected pipes ({','.join(accepted_pipes)}) before PROJECT_ROOT",
        )
    return pipes, (remaining[0] if remaining else None), None


def _optional_arg(args: list[str] | tuple[str, ...], index: int) -> str | None:
    if index >= len(args):
        return None
    value = args[index]
    if value.startswith("-"):
        return None
    return value


def _literal_arg(args: list[str] | tuple[str, ...], index: int) -> str | None:
    return None if index >= len(args) else args[index]


def _is_flag_like_literal_search_query(
    view: str,
    positionals: list[str],
    query_set: list[str],
    arg: str,
) -> bool:
    return (
        view == "fzf"
        and not positionals
        and not query_set
        and arg.startswith("-")
        and arg
        not in {
            "--view",
            "--package",
            "--owner",
            "--query",
            "--query-set",
            "--code",
            "--help",
            "-h",
        }
    )


def _search_view_supports_query_set(view: str) -> bool:
    return view == "fzf"
