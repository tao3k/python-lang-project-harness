"""Project policy for parser-visible pytest harness gates."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ._model import PythonHarnessFinding
from ._project_policy_catalog import PY_PROJ_R010, project_policy_rule
from ._source import path_location, source_line
from ._version import DISTRIBUTION_NAME

if TYPE_CHECKING:
    from collections.abc import Sequence

    from python_lang_parser import PythonModuleReport, PythonProjectMetadata


def project_pytest_gate_findings(
    metadata: PythonProjectMetadata,
    modules: Sequence[PythonModuleReport],
    pack_id: str,
) -> tuple[PythonHarnessFinding, ...]:
    """Return findings when a harness dependency is not wired into pytest."""

    if not declares_python_harness_surface(metadata):
        return ()
    if metadata.pytest_options.enables_python_project_harness:
        return ()
    if _has_explicit_harness_helper(modules):
        return ()

    rule = project_policy_rule(PY_PROJ_R010)
    return (
        PythonHarnessFinding(
            rule_id=rule.rule_id,
            pack_id=pack_id,
            severity=rule.severity,
            title=rule.title,
            summary=(
                f"{metadata.pyproject_path.name} declares the Python project harness "
                "surface without a parser-visible pytest gate."
            ),
            location=path_location(metadata.pyproject_path),
            requirement=rule.requirement,
            source_line=source_line(str(metadata.pyproject_path), 1),
            label="mount the parser-backed harness in pytest",
            labels=dict(rule.labels),
        ),
    )


def declares_python_harness_surface(metadata: PythonProjectMetadata) -> bool:
    """Return whether project metadata declares this harness as a dev surface."""

    distribution_name = _canonical_distribution_name(DISTRIBUTION_NAME)
    if _canonical_distribution_name(metadata.project_name or "") == distribution_name:
        return True
    if any(
        _canonical_distribution_name(dependency.name) == distribution_name
        for dependency in metadata.dependencies
    ):
        return True
    return any(
        entry_point.group == "pytest11"
        and entry_point.target_namespace[:1] == ("python_lang_project_harness",)
        for entry_point in metadata.entry_points
    )


def _has_explicit_harness_helper(
    modules: Sequence[PythonModuleReport],
) -> bool:
    for module in modules:
        for call in module.calls:
            if call.function == "python_project_harness_test":
                return True
            if call.function.endswith(".python_project_harness_test"):
                return True
    return False


def _canonical_distribution_name(value: str) -> str:
    return value.replace("_", "-").lower()
