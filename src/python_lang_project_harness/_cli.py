"""Command-line execution for the Python project harness."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import TextIO

from ._model import PythonHarnessConfig
from ._project_config import read_python_project_harness_config
from ._render import render_python_lang_harness, render_python_lang_harness_json
from ._runner import run_python_project_harness


def run_cli_from_env() -> int:
    """Run the CLI using process environment arguments."""

    return run_cli(sys.argv[1:])


def run_cli(
    args: list[str] | tuple[str, ...],
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    cwd: Path | None = None,
) -> int:
    """Run the default package-level Python harness CLI."""

    selected_stdout = sys.stdout if stdout is None else stdout
    selected_stderr = sys.stderr if stderr is None else stderr
    try:
        options = _CliOptions.parse(args)
        if options.help:
            selected_stdout.write(_help_text())
            return 0
        project_root = options.project_root(cwd)
        if not project_root.exists():
            raise ValueError(f"project root does not exist: {project_root}")
        report = run_python_project_harness(
            project_root,
            config=options.harness_config(project_root),
            include_tests=options.include_tests,
            source_dir_names=options.source_dir_names,
            test_dir_names=options.test_dir_names,
            extra_path_names=options.extra_path_names,
        )
        if options.json:
            selected_stdout.write(render_python_lang_harness_json(report))
            selected_stdout.write("\n")
        else:
            selected_stdout.write(render_python_lang_harness(report))
        return 0 if report.is_clean else 1
    except ValueError as error:
        selected_stderr.write(f"{error}\n")
        return 2


@dataclass(slots=True)
class _CliOptions:
    json: bool = False
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
        "python-project-harness [--json] [--no-tests] "
        "[--source-dir DIR] [--test-dir DIR] [--extra-path PATH] "
        "[--disable-rule RULE_ID] [--block-rule RULE_ID] [PROJECT_ROOT]\n\n"
        "Runs the default package-level Python harness.\n\n"
        "Compact text is the default output for humans and repair-oriented agents.\n"
        "Use --json to emit the structured PythonHarnessReport JSON shape.\n"
        "Repeat --source-dir or --test-dir to customize policy root classification.\n"
        "Repeat --extra-path to include external project paths.\n"
        "Repeat --disable-rule or --block-rule to customize policy by rule id.\n"
    )
