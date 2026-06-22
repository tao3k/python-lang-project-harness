"""Search runtime helpers for the Python harness CLI."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ._cli_args import ProtocolArgs


def _render_search_code_only(packet: dict[str, object]) -> str:
    items = packet.get("items", ())
    if not isinstance(items, list):
        return "\n"
    code = "\n".join(
        str(fields["code"])
        for item in items
        if isinstance(item, dict)
        and isinstance(fields := item.get("fields"), dict)
        and isinstance(fields.get("code"), str)
    )
    return f"{code}\n" if code else "\n"


def _run_search_harness(
    project_root: Path,
    args: ProtocolArgs,
) -> tuple[object, dict[str, object] | None]:
    from ._rule_packs import resolve_project_harness_config

    config = resolve_project_harness_config(
        project_root,
        None,
        rule_packs=None,
    )
    owner_items_report = _run_exact_owner_items_search(project_root, args)
    if owner_items_report is not None:
        return owner_items_report, {
            "reason": "owner-items-exact-owner-prefilter",
            "fields": {
                "paths": 1,
                "ownerPath": _owner_items_query_path(args) or "",
            },
        }
    if args.command != "search" or args.view != "fzf":
        from ._runner import run_python_project_harness

        return run_python_project_harness(project_root, config=config), None
    if config.include_hidden_dir_names:
        from ._runner import run_python_project_harness

        return run_python_project_harness(project_root, config=config), None
    from ._semantic_search_prefilter import prefilter_python_text_search_paths

    query_terms = args.query_set or (() if args.query is None else (args.query,))
    prefilter = prefilter_python_text_search_paths(
        project_root,
        query_terms,
        owner_path=args.owner_path,
    )
    if prefilter is None:
        from ._runner import run_python_project_harness

        return run_python_project_harness(project_root, config=config), None
    return _run_prefiltered_text_search(project_root, prefilter.paths), (
        prefilter.runtime_cost()
    )


def _run_exact_owner_items_search(
    project_root: Path,
    args: ProtocolArgs,
) -> _TextSearchReport | None:
    owner_path = _exact_owner_items_path(project_root, args)
    if owner_path is None:
        return None
    from python_lang_parser.parser import parse_python_file

    return _TextSearchReport(
        modules=(parse_python_file(owner_path),),
        project_scope=_fast_owner_items_scope(project_root, owner_path),
        root_paths=(str(owner_path),),
    )


def _exact_owner_items_path(project_root: Path, args: ProtocolArgs) -> Path | None:
    if (
        args.command != "search"
        or args.view != "owner"
        or "items" not in args.pipes
        or _owner_items_query_path(args) is None
    ):
        return None
    raw_path = Path(_owner_items_query_path(args) or "")
    owner_path = raw_path if raw_path.is_absolute() else project_root / raw_path
    try:
        resolved_root = project_root.resolve()
        resolved_owner = owner_path.resolve()
        resolved_owner.relative_to(resolved_root)
    except ValueError:
        return None
    if not resolved_owner.is_file() or resolved_owner.suffix != ".py":
        return None
    return resolved_owner


def _owner_items_query_path(args: ProtocolArgs) -> str | None:
    return args.owner_path or args.query


@dataclass(frozen=True, slots=True)
class _TextSearchReport:
    modules: tuple[object, ...]
    project_scope: _TextSearchScope
    findings: tuple[object, ...] = ()
    root_paths: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class _TextSearchScope:
    project_root: Path
    source_paths: tuple[Path, ...] = ()
    test_paths: tuple[Path, ...] = ()
    project_metadata: object | None = None
    project_paths: tuple[Path, ...] = ()
    extra_paths: tuple[Path, ...] = ()
    include_tests: bool = True
    fallback_paths: tuple[Path, ...] = ()

    @property
    def monitored_paths(self) -> tuple[Path, ...]:
        selected = (
            (*self.source_paths, *self.test_paths, *self.extra_paths)
            if self.include_tests
            else (*self.source_paths, *self.extra_paths)
        )
        return selected or self.fallback_paths


def _run_prefiltered_text_search(
    project_root: Path,
    paths: tuple[Path, ...],
) -> _TextSearchReport:
    from python_lang_parser.parser import parse_python_file

    return _TextSearchReport(
        modules=tuple(parse_python_file(path) for path in paths),
        project_scope=_fast_text_search_scope(project_root),
        root_paths=tuple(str(path) for path in paths),
    )


def _fast_text_search_scope(project_root: Path) -> _TextSearchScope:
    source_paths = tuple(
        path for name in ("src",) for path in (project_root / name,) if path.exists()
    )
    test_paths = tuple(
        path for name in ("tests",) for path in (project_root / name,) if path.exists()
    )
    return _TextSearchScope(
        project_root=project_root,
        source_paths=source_paths,
        test_paths=test_paths,
        fallback_paths=(project_root,),
    )


def _fast_owner_items_scope(project_root: Path, owner_path: Path) -> _TextSearchScope:
    return _TextSearchScope(
        project_root=project_root,
        fallback_paths=(owner_path,),
    )
