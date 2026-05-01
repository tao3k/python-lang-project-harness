"""Agent-facing reasoning-tree advice backed by parser-owned package facts."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from python_lang_parser import python_reasoning_tree_facts

from ._agent_policy_catalog import PY_AGENT_R007, agent_policy_rule
from ._model import PythonHarnessFinding
from ._source import path_location

if TYPE_CHECKING:
    from collections.abc import Sequence

    from python_lang_parser import PythonModuleReport

    from ._model import PythonProjectHarnessScope


def agent_reasoning_tree_findings(
    scope: PythonProjectHarnessScope,
    modules: Sequence[PythonModuleReport],
    pack_id: str,
) -> tuple[PythonHarnessFinding, ...]:
    """Return agent advice for package-tree navigation gaps."""

    facts = python_reasoning_tree_facts(
        modules,
        import_roots=_reasoning_tree_import_roots(scope),
        project_root=scope.project_root,
        project_metadata=scope.project_metadata,
    )
    modules_by_path = {
        module.path: module for module in modules if module.path is not None
    }
    rule = agent_policy_rule(PY_AGENT_R007)
    findings: list[PythonHarnessFinding] = []
    for branch in facts.branches:
        if branch.has_intent_doc:
            continue
        module = modules_by_path.get(branch.path)
        namespace = ".".join(branch.namespace)
        findings.append(
            PythonHarnessFinding(
                rule_id=rule.rule_id,
                pack_id=pack_id,
                severity=rule.severity,
                title=rule.title,
                summary=(
                    f"{branch.path} owns {branch.child_count} child modules "
                    f"under Python reasoning-tree branch {namespace!r} without "
                    "an intent docstring."
                ),
                location=path_location(branch.path),
                requirement=rule.requirement,
                source_line=None if module is None else module.source_line(1),
                label="add a package intent docstring to this branch",
                labels=dict(rule.labels),
            )
        )
    return tuple(findings)


def _reasoning_tree_import_roots(scope: PythonProjectHarnessScope) -> tuple[Path, ...]:
    if scope.source_paths:
        return scope.source_paths
    return scope.monitored_paths
