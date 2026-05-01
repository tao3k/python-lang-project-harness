from __future__ import annotations

from pathlib import Path

from python_lang_project_harness import python_project_harness_test

_PROJECT_ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "pyproject.toml").exists() and (parent / "src").exists()
)


test_python_lang_project_harness_self_policy = python_project_harness_test(
    _PROJECT_ROOT
)
