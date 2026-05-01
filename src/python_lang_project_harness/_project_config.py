"""Project-local pyproject configuration for Python harness policy."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from python_lang_parser import PythonDiagnosticSeverity

from ._model import PythonHarnessConfig

_TOOL_TABLE_NAME = "python-lang-project-harness"


def read_python_project_harness_config(
    project_root: str | Path,
) -> PythonHarnessConfig | None:
    """Read `[tool.python-lang-project-harness]` from `pyproject.toml`."""

    root = Path(project_root)
    pyproject_path = root / "pyproject.toml"
    if not pyproject_path.exists():
        return None

    try:
        payload = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError, UnicodeDecodeError):
        return None

    table = _table(_table(payload.get("tool")).get(_TOOL_TABLE_NAME))
    if not table:
        return None

    kwargs: dict[str, object] = {}
    _put_bool(kwargs, table, "include_tests")
    _put_string_tuple(kwargs, table, "source_dir_names")
    _put_string_tuple(kwargs, table, "test_dir_names")
    _put_string_tuple(kwargs, table, "extra_path_names")
    _put_string_frozenset(kwargs, table, "ignored_dir_names")
    _put_string_frozenset(kwargs, table, "disabled_rule_ids")
    _put_string_frozenset(kwargs, table, "blocking_rule_ids")
    _put_severity_frozenset(kwargs, table, "blocking_severities")
    return PythonHarnessConfig(**kwargs)


def _put_bool(
    kwargs: dict[str, object],
    table: dict[str, Any],
    key: str,
) -> None:
    value = table.get(key)
    if value is None:
        return
    if not isinstance(value, bool):
        raise ValueError(f"{_TOOL_TABLE_NAME}.{key} must be a boolean")
    kwargs[key] = value


def _put_string_tuple(
    kwargs: dict[str, object],
    table: dict[str, Any],
    key: str,
) -> None:
    value = table.get(key)
    if value is None:
        return
    kwargs[key] = _string_tuple(value, key=key)


def _put_string_frozenset(
    kwargs: dict[str, object],
    table: dict[str, Any],
    key: str,
) -> None:
    value = table.get(key)
    if value is None:
        return
    kwargs[key] = frozenset(_string_tuple(value, key=key))


def _put_severity_frozenset(
    kwargs: dict[str, object],
    table: dict[str, Any],
    key: str,
) -> None:
    value = table.get(key)
    if value is None:
        return
    kwargs[key] = frozenset(_severity(value) for value in _string_tuple(value, key=key))


def _table(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _string_tuple(value: object, *, key: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{_TOOL_TABLE_NAME}.{key} must be a list of strings")
    values: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str):
            raise ValueError(f"{_TOOL_TABLE_NAME}.{key} must be a list of strings")
        if item in seen:
            continue
        seen.add(item)
        values.append(item)
    return tuple(values)


def _severity(value: str) -> PythonDiagnosticSeverity:
    try:
        return PythonDiagnosticSeverity(value)
    except ValueError as error:
        raise ValueError(
            f"{_TOOL_TABLE_NAME}.blocking_severities has unknown severity: {value}"
        ) from error
