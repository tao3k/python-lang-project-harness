"""Command-line execution for the Python project harness."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import TextIO

from ._agent_snapshot import render_python_project_harness_agent_snapshot_report
from ._model import PythonHarnessConfig
from ._project_config import read_python_project_harness_config
from ._render import render_python_lang_harness, render_python_lang_harness_json
from ._runner import run_python_project_harness
from ._semantic_language import (
    PYTHON_BINARY,
    PYTHON_LANGUAGE_ID,
    PYTHON_PROVIDER_ID,
    PYTHON_PROVIDER_NAMESPACE,
    SEMANTIC_LANGUAGE_PROTOCOL_ID,
    SEMANTIC_LANGUAGE_REGISTRY_VERSION,
    python_semantic_language_registration,
    python_semantic_search_view_descriptor,
    semantic_language_registry_document,
)
from ._semantic_search import (
    PythonSemanticSearchOptions,
    build_python_semantic_search_packet,
    render_python_semantic_search_packet,
    render_python_semantic_search_packet_json,
)


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
    protocol_args = _ProtocolArgs.parse(args)
    if protocol_args is not None:
        return _run_protocol_cli(
            protocol_args,
            stdout=selected_stdout,
            stderr=selected_stderr,
            stdin="" if stdin is None else stdin,
            cwd=selected_cwd,
        )
    try:
        options = _CliOptions.parse(args)
        if options.help:
            selected_stdout.write(_help_text())
            return 0
        project_root = options.project_root(cwd)
        if not project_root.exists():
            raise ValueError(f"project root does not exist: {project_root}")
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


@dataclass(slots=True)
class _ProtocolArgs:
    command: str
    view: str | None = None
    action: str | None = None
    query: str | None = None
    project_root: Path | None = None
    package_path: Path | None = None
    pipes: tuple[str, ...] = ()
    json: bool = False
    render_mode: str | None = None
    error: str | None = None

    @classmethod
    def parse(cls, args: list[str] | tuple[str, ...]) -> _ProtocolArgs | None:
        command = args[0] if args else None
        if command == "search":
            return cls._parse_search(args[1:])
        if command == "check":
            return cls._parse_check(args[1:])
        if command == "agent":
            return cls._parse_agent(args[1:])
        return None

    @classmethod
    def _parse_search(cls, args: list[str] | tuple[str, ...]) -> _ProtocolArgs:
        view = args[0] if args else None
        if view is None or view in {"--help", "-h"}:
            return cls(
                "error",
                error=(
                    "usage: py-harness search "
                    "<workspace|prime|owner|dependency|deps|api|symbol|import|tests|text|ingest> "
                    "... [--json] [--package PATH] [PROJECT_ROOT]"
                ),
            )
        descriptor = python_semantic_search_view_descriptor(view)
        if descriptor is None:
            return cls("error", error=f"unknown search view: {view}")
        json_output = False
        render_mode: str | None = None
        package_path: Path | None = None
        positionals: list[str] = []
        index = 1
        while index < len(args):
            arg = args[index]
            if arg == "--json":
                json_output = True
            elif arg == "--view":
                value = _optional_arg(args, index + 1)
                if value not in {"graph", "hits", "both", "seeds"}:
                    return cls(
                        "error",
                        error="--view requires graph, hits, both, or seeds",
                    )
                render_mode = value
                index += 1
            elif arg == "--package":
                value = _optional_arg(args, index + 1)
                if value is None:
                    return cls("error", error="--package requires a package path")
                package_path = Path(value)
                index += 1
            elif arg.startswith("-"):
                return cls("error", error=f"unknown search option: {arg}")
            else:
                positionals.append(arg)
            index += 1
        if descriptor["requiresQuery"]:
            query = positionals[0] if positionals else None
            if query is None:
                return cls("error", error=f"search {view} requires a query")
            pipes, project_root, error = _parse_search_pipe_positionals(
                positionals[1:],
                descriptor.get("acceptedPipes", ()),
            )
            if error is not None:
                return cls("error", error=error)
            return cls(
                "search",
                view=view,
                query=query,
                project_root=None if project_root is None else Path(project_root),
                package_path=package_path,
                pipes=tuple(pipes),
                json=json_output,
                render_mode=render_mode,
            )
        if len(positionals) > 1:
            return cls("error", error="expected at most one PROJECT_ROOT argument")
        return cls(
            "search",
            view=view,
            project_root=None if not positionals else Path(positionals[0]),
            package_path=package_path,
            json=json_output,
            render_mode=render_mode,
        )

    @classmethod
    def _parse_check(cls, args: list[str] | tuple[str, ...]) -> _ProtocolArgs:
        json_output = False
        positionals: list[str] = []
        for arg in args:
            if arg == "--json":
                json_output = True
            elif arg in {"--changed", "--full"}:
                continue
            elif arg in {"--help", "-h"}:
                return cls(
                    "error",
                    error="usage: py-harness check [--changed | --full] [--json] [PROJECT_ROOT]",
                )
            elif arg.startswith("-"):
                return cls("error", error=f"unknown check option: {arg}")
            else:
                positionals.append(arg)
        if len(positionals) > 1:
            return cls("error", error="expected at most one PROJECT_ROOT argument")
        return cls(
            "check",
            project_root=None if not positionals else Path(positionals[0]),
            json=json_output,
        )

    @classmethod
    def _parse_agent(cls, args: list[str] | tuple[str, ...]) -> _ProtocolArgs:
        action = args[0] if args else "doctor"
        if action != "doctor":
            return cls("error", error=f"unknown agent action: {action}")
        json_output = False
        positionals: list[str] = []
        for arg in args[1:]:
            if arg == "--json":
                json_output = True
            elif arg in {"--help", "-h"}:
                continue
            elif arg.startswith("-"):
                return cls("error", error=f"unknown agent option: {arg}")
            else:
                positionals.append(arg)
        if len(positionals) > 1:
            return cls("error", error="expected at most one PROJECT_ROOT argument")
        return cls(
            "agent",
            action="doctor",
            project_root=None if not positionals else Path(positionals[0]),
            json=json_output,
        )


def _run_protocol_cli(
    args: _ProtocolArgs,
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
        if args.json:
            stdout.write(
                _render_agent_doctor_json(project_root),
            )
        else:
            stdout.write(_render_agent_doctor(project_root))
        return 0
    try:
        report = run_python_project_harness(project_root)
        if args.command == "check":
            if args.json:
                stdout.write(render_python_lang_harness_json(report))
                stdout.write("\n")
            else:
                stdout.write(render_python_lang_harness(report))
            return 0 if report.is_clean else 1
        packet = build_python_semantic_search_packet(
            report,
            PythonSemanticSearchOptions(
                view=args.view or "prime",
                query=args.query,
                pipes=args.pipes,
                render_mode=args.render_mode,
                stdin=stdin,
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


def _render_agent_doctor(project_root: Path) -> str:
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

    return (
        json.dumps(
            semantic_language_registry_document(str(project_root)),
            indent=2,
        )
        + "\n"
    )


@dataclass(slots=True)
class _CliOptions:
    json: bool = False
    agent_snapshot: bool = False
    help: bool = False
    include_tests: bool | None = None
    source_dir_values: list[str] = field(default_factory=list)
    test_dir_values: list[str] = field(default_factory=list)
    extra_path_values: list[str] = field(default_factory=list)
    disabled_rule_values: list[str] = field(default_factory=list)
    blocking_rule_values: list[str] = field(default_factory=list)
    paths: list[Path] = field(default_factory=list)

    @classmethod
    def parse(cls, args: list[str] | tuple[str, ...]) -> _CliOptions:
        options = cls()
        positional_only = False
        index = 0
        while index < len(args):
            arg = args[index]
            index += 1
            if positional_only:
                options.paths.append(Path(arg))
                continue
            match arg:
                case "--":
                    positional_only = True
                case "--json":
                    options.json = True
                case "--agent-snapshot":
                    options.agent_snapshot = True
                case "--no-tests":
                    options.include_tests = False
                case "--source-dir":
                    options.source_dir_values.append(
                        _option_value(args, index, "--source-dir")
                    )
                    index += 1
                case "--test-dir":
                    options.test_dir_values.append(
                        _option_value(args, index, "--test-dir")
                    )
                    index += 1
                case "--extra-path":
                    options.extra_path_values.append(
                        _option_value(args, index, "--extra-path")
                    )
                    index += 1
                case "--disable-rule":
                    options.disabled_rule_values.append(
                        _option_value(args, index, "--disable-rule")
                    )
                    index += 1
                case "--block-rule":
                    options.blocking_rule_values.append(
                        _option_value(args, index, "--block-rule")
                    )
                    index += 1
                case "--help" | "-h":
                    options.help = True
                case value if value.startswith("-"):
                    raise ValueError(f"unknown option: {value}")
                case value:
                    options.paths.append(Path(value))
        if len(options.paths) > 1:
            raise ValueError("expected at most one PROJECT_ROOT argument")
        if options.json and options.agent_snapshot:
            raise ValueError("--json and --agent-snapshot are mutually exclusive")
        return options

    def project_root(self, cwd: Path | None) -> Path:
        if self.paths:
            return self.paths[0]
        if cwd is not None:
            return cwd
        return Path.cwd()

    @property
    def source_dir_names(self) -> tuple[str, ...] | None:
        """Return explicit source roots, when the CLI supplied any."""

        if not self.source_dir_values:
            return None
        return tuple(self.source_dir_values)

    @property
    def test_dir_names(self) -> tuple[str, ...] | None:
        """Return explicit test roots, when the CLI supplied any."""

        if not self.test_dir_values:
            return None
        return tuple(self.test_dir_values)

    @property
    def extra_path_names(self) -> tuple[str, ...] | None:
        """Return explicit extra project paths, when the CLI supplied any."""

        if not self.extra_path_values:
            return None
        return tuple(self.extra_path_values)

    def harness_config(self, project_root: Path) -> PythonHarnessConfig | None:
        """Return CLI policy config when rule-level options were supplied."""

        if not self.disabled_rule_values and not self.blocking_rule_values:
            return None
        base_config = read_python_project_harness_config(project_root)
        config = base_config if base_config is not None else PythonHarnessConfig()
        return replace(
            config,
            disabled_rule_ids=(
                frozenset(self.disabled_rule_values)
                if self.disabled_rule_values
                else config.disabled_rule_ids
            ),
            blocking_rule_ids=(
                frozenset(self.blocking_rule_values)
                if self.blocking_rule_values
                else config.blocking_rule_ids
            ),
        )


def _option_value(
    args: list[str] | tuple[str, ...],
    index: int,
    option_name: str,
) -> str:
    if index >= len(args):
        raise ValueError(f"missing value for {option_name}")
    value = args[index]
    if value.startswith("-"):
        raise ValueError(f"missing value for {option_name}")
    return value


def _help_text() -> str:
    return (
        "py-harness — Python semantic search and project harness\n\n"
        "Usage:\n"
        "  py-harness search <view> ... [--json] [--package PATH] [PROJECT_ROOT]\n"
        "  py-harness check [--changed | --full] [--json] [PROJECT_ROOT]\n"
        "  py-harness agent doctor [--json] [PROJECT_ROOT]\n"
        "  py-harness [--json | --agent-snapshot] [--no-tests] "
        "[--source-dir DIR] [--test-dir DIR] [--extra-path PATH] "
        "[--disable-rule RULE_ID] [--block-rule RULE_ID] [PROJECT_ROOT]\n\n"
        "SEARCH VIEWS\n"
        "  search workspace          Workspace package/router index\n"
        "  search prime              Project reasoning-tree map\n"
        "  search owner <path>       Owner graph slice\n"
        "  search dependency <pkg>   Dependency manifest and local import usage\n"
        "  search deps <pkg[@ver][::api]>\n"
        "                             Versioned dependency API usage evidence\n"
        "  search api <query>        Parser-owned public API facts\n"
        "  search symbol <name>      Symbol/export definitions\n"
        "  search import <query>     Import owner edges\n"
        "  search tests <owner>      Tests that import an owner\n"
        "  search text <query>       Owner-grouped path/export/source-text search\n"
        "  search text <query> owner tests\n"
        "                             Minimal final-only text -> owner -> tests pipe\n"
        "  search ingest             Detect stdin shape and group hits by owner\n\n"
        "CHECK\n"
        "  check --changed           Fast lane alias; currently delegates to project check\n"
        "  check --full              Full project harness check\n"
        "  check --json              Structured PythonHarnessReport JSON\n\n"
        "AGENT\n"
        "  agent doctor              Print semantic-language provider readiness\n"
        "  agent doctor --json       Semantic language registry document\n\n"
        "DIRECT CHECK\n"
        "The no-command form still runs the default package-level Python harness.\n\n"
        "Compact text is the default output for humans and repair-oriented agents.\n"
        "Use --json to emit the structured PythonHarnessReport JSON shape.\n"
        "Use --agent-snapshot to emit parser facts for project repair agents.\n"
        "Repeat --source-dir or --test-dir to customize policy root classification.\n"
        "Repeat --extra-path to include external project paths.\n"
        "Repeat --disable-rule or --block-rule to customize policy by rule id.\n"
        "\nEXAMPLES\n"
        "  py-harness search workspace .\n"
        "  py-harness search prime .\n"
        "  py-harness search text PythonSemanticSearchOptions owner tests .\n"
        '  rg -n "PythonSemanticSearchOptions" src tests | py-harness search ingest .\n'
        "  py-harness check --full .\n"
        "  py-harness agent doctor --json .\n"
    )
