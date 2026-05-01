"""Pytest plugin entry point for dev-dependency harness mounting."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from python_lang_parser import PythonDiagnosticSeverity

from ._model import PythonHarnessConfig
from ._runner import assert_python_project_harness_clean

if TYPE_CHECKING:
    from collections.abc import Sequence


_ENABLE_OPTION = "--python-project-harness"
_ROOT_OPTION = "--python-project-harness-root"
_NO_TESTS_OPTION = "--python-project-harness-no-tests"
_SOURCE_DIR_OPTION = "--python-project-harness-source-dir"
_TEST_DIR_OPTION = "--python-project-harness-test-dir"
_EXTRA_PATH_OPTION = "--python-project-harness-extra-path"
_DISABLE_RULE_OPTION = "--python-project-harness-disable-rule"
_BLOCK_RULE_OPTION = "--python-project-harness-block-rule"
_ERROR_ONLY_OPTION = "--python-project-harness-error-only"
_NO_ADVICE_OPTION = "--python-project-harness-no-advice"


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register Python project harness pytest options."""

    group = parser.getgroup("python-lang-project-harness")
    group.addoption(
        _ENABLE_OPTION,
        action="store_true",
        default=False,
        help="Collect and run the python-lang-project-harness policy test.",
    )
    group.addoption(
        _ROOT_OPTION,
        action="store",
        default=None,
        metavar="PATH",
        help="Project root for the harness test. Defaults to pytest rootdir.",
    )
    group.addoption(
        _NO_TESTS_OPTION,
        action="store_true",
        default=False,
        help="Do not parse test files; pytest layout checks still run.",
    )
    group.addoption(
        _SOURCE_DIR_OPTION,
        action="append",
        default=[],
        metavar="NAME",
        help="Source directory name to scan. Can be provided more than once.",
    )
    group.addoption(
        _TEST_DIR_OPTION,
        action="append",
        default=[],
        metavar="NAME",
        help="Test directory name to scan. Can be provided more than once.",
    )
    group.addoption(
        _EXTRA_PATH_OPTION,
        action="append",
        default=[],
        metavar="NAME",
        help="Extra project path name to scan. Can be provided more than once.",
    )
    group.addoption(
        _DISABLE_RULE_OPTION,
        action="append",
        default=[],
        metavar="RULE_ID",
        help="Harness rule id to suppress. Can be provided more than once.",
    )
    group.addoption(
        _BLOCK_RULE_OPTION,
        action="append",
        default=[],
        metavar="RULE_ID",
        help="Harness rule id to treat as blocking. Can be provided more than once.",
    )
    group.addoption(
        _ERROR_ONLY_OPTION,
        action="store_true",
        default=False,
        help="Only fail the pytest harness item for parser errors.",
    )
    group.addoption(
        _NO_ADVICE_OPTION,
        action="store_true",
        default=False,
        help="Hide non-blocking advice from assertion output.",
    )


def pytest_collection_modifyitems(
    session: pytest.Session,
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    """Insert one explicit harness item when the plugin option is enabled."""

    if not config.getoption(_ENABLE_OPTION):
        return
    item = PythonProjectHarnessItem.from_parent(
        session,
        name="python-project-harness",
    )
    items.insert(0, item)


class PythonProjectHarnessItem(pytest.Item):
    """Pytest item that runs the parser-backed project harness."""

    def runtest(self) -> None:
        """Run the configured project harness and raise a compact assertion."""

        assert_python_project_harness_clean(
            _project_root(self.config),
            config=_harness_config(self.config),
            severities=_blocking_severities(self.config),
            include_tests=not self.config.getoption(_NO_TESTS_OPTION),
            source_dir_names=_optional_tuple(self.config.getoption(_SOURCE_DIR_OPTION)),
            test_dir_names=_optional_tuple(self.config.getoption(_TEST_DIR_OPTION)),
            extra_path_names=_optional_tuple(self.config.getoption(_EXTRA_PATH_OPTION)),
            include_advice=not self.config.getoption(_NO_ADVICE_OPTION),
        )

    def repr_failure(
        self,
        excinfo: pytest.ExceptionInfo[BaseException],
        style: str | None = None,
    ) -> str:
        """Return compact harness assertion text without pytest traceback noise."""

        if isinstance(excinfo.value, AssertionError):
            return str(excinfo.value)
        return super().repr_failure(excinfo, style=style)

    def reportinfo(self) -> tuple[Path, int, str]:
        """Return stable report metadata for pytest output."""

        return (_project_root(self.config), 0, "python project harness")


def _project_root(config: pytest.Config) -> Path:
    configured_root = config.getoption(_ROOT_OPTION)
    if configured_root:
        return Path(configured_root)
    return Path(config.rootpath)


def _blocking_severities(
    config: pytest.Config,
) -> frozenset[PythonDiagnosticSeverity] | None:
    if config.getoption(_ERROR_ONLY_OPTION):
        return frozenset({PythonDiagnosticSeverity.ERROR})
    return None


def _harness_config(config: pytest.Config) -> PythonHarnessConfig:
    return PythonHarnessConfig(
        disabled_rule_ids=frozenset(config.getoption(_DISABLE_RULE_OPTION)),
        blocking_rule_ids=frozenset(config.getoption(_BLOCK_RULE_OPTION)),
    )


def _optional_tuple(values: Sequence[str]) -> tuple[str, ...] | None:
    return tuple(values) if values else None
