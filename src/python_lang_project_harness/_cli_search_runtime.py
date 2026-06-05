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
