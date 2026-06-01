"""Command-line execution for the Python project harness."""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path
from typing import TextIO

from ._cli_args import CliOptions, ProtocolArgs, help_text


def run_cli_from_env() -> int:
    """Run the CLI using process environment arguments."""

    stdin = "" if sys.stdin.isatty() else sys.stdin.read()
    return run_cli(sys.argv[1:], stdin=stdin)


def run_cli(
    args: list[str] | tuple[str, ...],
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    stdin: str | None = None,
    cwd: Path | None = None,
) -> int:
    """Run the default package-level Python harness CLI."""

    selected_stdout = sys.stdout if stdout is None else stdout
    selected_stderr = sys.stderr if stderr is None else stderr
    selected_cwd = Path.cwd() if cwd is None else cwd
    protocol_args = ProtocolArgs.parse(args)
    if protocol_args is not None:
        return _run_protocol_cli(
            protocol_args,
            stdout=selected_stdout,
            stderr=selected_stderr,
            stdin="" if stdin is None else stdin,
            cwd=selected_cwd,
        )
    try:
        options = CliOptions.parse(args)
        if options.help:
            selected_stdout.write(help_text())
            return 0
        project_root = options.project_root(cwd)
        if not project_root.exists():
            raise ValueError(f"project root does not exist: {project_root}")
        from ._render import render_python_lang_harness, render_python_lang_harness_json
        from ._runner import run_python_project_harness

        config = options.harness_config(project_root)
        report = run_python_project_harness(
            project_root,
            config=config,
            include_tests=options.include_tests,
            source_dir_names=options.source_dir_names,
            test_dir_names=options.test_dir_names,
            extra_path_names=options.extra_path_names,
        )
        if options.json:
            selected_stdout.write(render_python_lang_harness_json(report))
            selected_stdout.write("\n")
        elif options.agent_snapshot:
            from ._agent_snapshot import (
                render_python_project_harness_agent_snapshot_report,
            )
            from ._model import PythonHarnessConfig
            from ._project_config import read_python_project_harness_config

            selected_stdout.write(
                render_python_project_harness_agent_snapshot_report(
                    report,
                    config=(
                        config
                        or read_python_project_harness_config(project_root)
                        or PythonHarnessConfig()
                    ),
                )
            )
        else:
            selected_stdout.write(render_python_lang_harness(report))
        return 0 if report.is_clean else 1
    except ValueError as error:
        selected_stderr.write(f"{error}\n")
        return 2


def _run_protocol_cli(
    args: ProtocolArgs,
    *,
    stdout: TextIO,
    stderr: TextIO,
    stdin: str,
    cwd: Path,
) -> int:
    if args.command == "error":
        stderr.write(f"{args.error}\n")
        return 2
    project_root = (cwd / args.project_root).resolve() if args.project_root else cwd
    if args.package_path is not None:
        project_root = (project_root / args.package_path).resolve()
    if args.command == "agent":
        if args.action == "guide":
            stdout.write(_render_agent_guide(project_root))
            return 0
        if args.json:
            stdout.write(
                _render_agent_doctor_json(project_root),
            )
        else:
            stdout.write(_render_agent_doctor(project_root))
        return 0
    try:
        report, runtime_cost = _run_search_harness(project_root, args)
        if args.command == "check":
            from ._render import (
                render_python_lang_harness,
                render_python_lang_harness_json,
            )

            if args.json:
                stdout.write(render_python_lang_harness_json(report))
                stdout.write("\n")
            else:
                stdout.write(render_python_lang_harness(report))
            return 0 if report.is_clean else 1
        from ._semantic_search import (
            PythonSemanticSearchOptions,
            build_python_semantic_search_packet,
            render_python_semantic_search_packet,
            render_python_semantic_search_packet_json,
        )

        packet = build_python_semantic_search_packet(
            report,
            PythonSemanticSearchOptions(
                view=args.view or "prime",
                query=args.query,
                query_set=args.query_set,
                owner_path=args.owner_path,
                pipes=args.pipes,
                render_mode=args.render_mode,
                stdin=stdin,
                runtime_cost=runtime_cost,
            ),
        )
        stdout.write(
            render_python_semantic_search_packet_json(packet)
            if args.json
            else render_python_semantic_search_packet(packet)
        )
        return 0
    except ValueError as error:
        stderr.write(f"{error}\n")
        return 3


def _run_search_harness(
    project_root: Path,
    args: ProtocolArgs,
) -> tuple[object, dict[str, object] | None]:
    from ._runner import run_python_lang_harness, run_python_project_harness

    if args.command != "search" or args.view != "text":
        return run_python_project_harness(project_root), None
    from ._discovery import python_project_harness_scope
    from ._semantic_search_prefilter import prefilter_python_text_search_paths

    query_terms = args.query_set or (() if args.query is None else (args.query,))
    prefilter = prefilter_python_text_search_paths(
        project_root,
        query_terms,
        owner_path=args.owner_path,
    )
    if prefilter is None:
        return run_python_project_harness(project_root), None
    report = run_python_lang_harness(prefilter.paths)
    return replace(
        report,
        project_scope=python_project_harness_scope(project_root),
    ), prefilter.runtime_cost()


def _render_agent_doctor(project_root: Path) -> str:
    from ._semantic_language import (
        PYTHON_BINARY,
        PYTHON_LANGUAGE_ID,
        PYTHON_PROVIDER_ID,
        PYTHON_PROVIDER_NAMESPACE,
        SEMANTIC_LANGUAGE_PROTOCOL_ID,
        SEMANTIC_LANGUAGE_REGISTRY_VERSION,
        python_semantic_language_registration,
    )

    registration = python_semantic_language_registration()
    return (
        "\n".join(
            (
                "[agent-doctor] "
                f"status=ok protocol={SEMANTIC_LANGUAGE_PROTOCOL_ID} "
                f"registry=semantic-language-registry.v{SEMANTIC_LANGUAGE_REGISTRY_VERSION}",
                f"|project {project_root}",
                (
                    f"|language id={PYTHON_LANGUAGE_ID} provider={PYTHON_PROVIDER_ID} "
                    f"binary={PYTHON_BINARY}"
                ),
                f"|namespace {PYTHON_PROVIDER_NAMESPACE}",
                f"|method {','.join(registration['methods'])}",
                "|schema semantic-search-packet.v1",
            )
        )
        + "\n"
    )


def _render_agent_doctor_json(project_root: Path) -> str:
    import json

    from ._semantic_language import semantic_language_registry_document

    return (
        json.dumps(
            semantic_language_registry_document(str(project_root)),
            separators=(",", ":"),
        )
        + "\n"
    )


def _render_agent_guide(project_root: Path) -> str:
    root = str(project_root)
    return (
        "\n".join(
            (
                f"[py-harness-guide] project={root}",
                f"|cmd py-harness search prime --view seeds {root}",
                f"|cmd py-harness search owner <owner-path> --view seeds {root}",
                f"|cmd py-harness search text <query> owner tests --view seeds {root}",
                f"|cmd py-harness search deps <pkg[@ver][::api]> {root}",
                f"|pipe <candidate-lines> | py-harness search ingest --view seeds {root}",
                f"|cmd py-harness check --changed {root}",
                "|rule agent hook install/runtime is owned by semantic-agent-hook",
                "|rule use installed py-harness binary; run one command at a time; no raw Python source reads",
                "|subagent give one |cmd or |pipe line; require evidence/missing/next/risk",
            )
        )
        + "\n"
    )
