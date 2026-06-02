"""Query command argument parsing for the Python harness CLI."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._cli_args import ProtocolArgs


def parse_query_args(
    args_type: type[ProtocolArgs],
    args: list[str] | tuple[str, ...],
) -> ProtocolArgs:
    """Parse py-harness query arguments into protocol args."""
    if args and args[0] in {"--help", "-h"}:
        return args_type("help")
    state = _QueryParseState()
    index = 0
    while index < len(args):
        index = _consume_query_arg(args_type, state, args, index)
        if isinstance(index, ProtocolArgError):
            return args_type("error", error=index.message)
    return _query_args_result(args_type, state)


class ProtocolArgError:
    """Small sentinel for parse errors without widening ProtocolArgs."""

    def __init__(self, message: str) -> None:
        self.message = message


class _QueryParseState:
    json_output: bool = False
    names_only: bool = False
    code_only: bool = False
    package_path: Path | None = None
    from_hook: str | None = None
    selector: str | None = None
    terms: list[str]
    positionals: list[str]

    def __init__(self) -> None:
        self.terms = []
        self.positionals = []


def _consume_query_arg(
    args_type: type[ProtocolArgs],
    state: _QueryParseState,
    args: list[str] | tuple[str, ...],
    index: int,
) -> int | ProtocolArgError:
    del args_type
    arg = args[index]
    if arg in {"--term", "--query"}:
        return _consume_query_term(state, args, index, arg)
    if arg in {"--names-only", "--code", "--json"}:
        _set_query_flag(state, arg)
        return index + 1
    if arg in {"--from-hook", "--selector", "--package"}:
        return _consume_query_option(state, args, index, arg)
    if arg in {"--help", "-h"}:
        return ProtocolArgError(_QUERY_USAGE)
    if arg.startswith("-"):
        return ProtocolArgError(f"unknown query option: {arg}")
    state.positionals.append(arg)
    return index + 1


def _consume_query_term(
    state: _QueryParseState,
    args: list[str] | tuple[str, ...],
    index: int,
    arg: str,
) -> int | ProtocolArgError:
    value = _optional_arg(args, index + 1)
    if value is None:
        return ProtocolArgError(f"{arg} requires a value")
    if arg == "--query":
        state.terms.extend(term.strip() for term in value.split("|") if term.strip())
    else:
        state.terms.append(value)
    return index + 2


def _set_query_flag(state: _QueryParseState, arg: str) -> None:
    if arg == "--names-only":
        state.names_only = True
    elif arg == "--code":
        state.code_only = True
    else:
        state.json_output = True


def _consume_query_option(
    state: _QueryParseState,
    args: list[str] | tuple[str, ...],
    index: int,
    arg: str,
) -> int | ProtocolArgError:
    value = _optional_arg(args, index + 1)
    if value is None:
        return ProtocolArgError(f"{arg} requires {_query_option_value_name(arg)}")
    if arg == "--from-hook":
        state.from_hook = value
    elif arg == "--selector":
        state.selector = value
    else:
        state.package_path = Path(value)
    return index + 2


def _query_args_result(
    args_type: type[ProtocolArgs],
    state: _QueryParseState,
) -> ProtocolArgs:
    error = _query_args_error(state)
    if error is not None:
        return args_type("error", error=error)
    owner_path = (
        _owner_path_from_query_selector(state.selector)
        if state.selector is not None
        else state.positionals[0]
    )
    project_root = _query_project_root(state)
    return args_type(
        "query",
        owner_path=owner_path,
        selector=state.selector,
        query_set=tuple(state.terms),
        project_root=project_root,
        package_path=state.package_path,
        json=state.json_output,
        names_only=_query_names_only(state),
        code_only=state.code_only,
    )


def _query_args_error(state: _QueryParseState) -> str | None:
    if state.from_hook is not None and state.from_hook != "direct-source-read":
        return f"unsupported query hook route: {state.from_hook}"
    if not state.selector and not state.positionals:
        return "query requires an owner path"
    if len(state.positionals) > (2 if state.selector is None else 1):
        return "expected owner path and optional PROJECT_ROOT"
    if not state.terms and state.from_hook != "direct-source-read":
        return "query requires at least one --term"
    if state.json_output and state.code_only:
        return "--code cannot be combined with --json"
    if state.names_only and state.code_only:
        return "--code cannot be combined with --names-only"
    return None


def _query_project_root(state: _QueryParseState) -> Path | None:
    if state.selector is None:
        return None if len(state.positionals) == 1 else Path(state.positionals[1])
    return None if not state.positionals else Path(state.positionals[0])


def _owner_path_from_query_selector(selector: str | None) -> str | None:
    if selector is None:
        return None
    normalized = selector.replace("\\", "/").removeprefix("owner:")
    if any(marker in normalized for marker in ("*", "{", "}")):
        return None
    return re.sub(r":[1-9][0-9]*(?:-[1-9][0-9]*)?$", "", normalized)


def _query_names_only(state: _QueryParseState) -> bool:
    if state.names_only:
        return True
    return bool(
        not state.terms
        and state.from_hook == "direct-source-read"
        and not state.code_only
        and not state.json_output
        and not _selector_has_line_range(state.selector)
    )


def _selector_has_line_range(selector: str | None) -> bool:
    if selector is None:
        return False
    normalized = selector.replace("\\", "/").removeprefix("owner:")
    if any(marker in normalized for marker in ("*", "{", "}")):
        return False
    return re.search(r":[1-9][0-9]*(?:-[1-9][0-9]*)?$", normalized) is not None


def _query_option_value_name(arg: str) -> str:
    return {
        "--from-hook": "a hook reason",
        "--selector": "an owner path",
        "--package": "a package path",
    }[arg]


def _optional_arg(args: list[str] | tuple[str, ...], index: int) -> str | None:
    if index >= len(args):
        return None
    value = args[index]
    if value.startswith("-"):
        return None
    return value


_QUERY_USAGE = (
    "usage: py-harness query <owner-path> --term <symbol> "
    "[--term <symbol>] [--names-only] [--json] [--package PATH] [PROJECT_ROOT]"
)
