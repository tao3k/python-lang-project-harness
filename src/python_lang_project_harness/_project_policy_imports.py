"""Project import-name metadata policy backed by parser reasoning facts."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from python_lang_parser import python_reasoning_tree_facts

from ._model import PythonHarnessFinding
from ._project_policy_catalog import PY_PROJ_R008, project_policy_rule
from ._source import path_location, source_line

if TYPE_CHECKING:
    from collections.abc import Sequence

    from python_lang_parser import PythonModuleReport

    from ._model import PythonProjectHarnessScope
    from ._project_metadata import PythonProjectMetadata


def project_import_name_findings(
    scope: PythonProjectHarnessScope,
    metadata: PythonProjectMetadata,
    modules: Sequence[PythonModuleReport],
    pack_id: str,
) -> tuple[PythonHarnessFinding, ...]:
    """Return findings for declared import names not backed by parser owners."""

    rule = project_policy_rule(PY_PROJ_R008)
    facts = python_reasoning_tree_facts(
        modules,
        import_roots=_reasoning_tree_import_roots(scope, metadata),
        project_root=scope.project_root,
        project_metadata=metadata,
    )
    known_namespaces = {node.namespace for node in facts.nodes if node.namespace}
    findings: list[PythonHarnessFinding] = []
    findings.extend(_ambiguous_import_name_findings(metadata, pack_id))
    for import_name in metadata.import_names:
        if import_name.name == "" or import_name.namespace in known_namespaces:
            continue
        findings.append(
            PythonHarnessFinding(
                rule_id=rule.rule_id,
                pack_id=pack_id,
                severity=rule.severity,
                title=rule.title,
                summary=(
                    f"{metadata.pyproject_path.name} declares import name "
                    f"{import_name.name!r}, but the parser did not find a "
                    "matching project module owner."
                ),
                location=path_location(metadata.pyproject_path),
                requirement=rule.requirement,
                source_line=source_line(str(metadata.pyproject_path), 1),
                label="align this declared import name with parser-visible code",
                labels=dict(rule.labels),
            )
        )
    return tuple(findings)


def _ambiguous_import_name_findings(
    metadata: PythonProjectMetadata,
    pack_id: str,
) -> tuple[PythonHarnessFinding, ...]:
    import_namespaces = {item.name for item in metadata.import_namespaces}
    ambiguous = tuple(
        item
        for item in metadata.import_names
        if item.name != "" and item.name in import_namespaces
    )
    if not ambiguous:
        return ()

    rule = project_policy_rule(PY_PROJ_R008)
    return tuple(
        PythonHarnessFinding(
            rule_id=rule.rule_id,
            pack_id=pack_id,
            severity=rule.severity,
            title=rule.title,
            summary=(
                f"{metadata.pyproject_path.name} declares {item.name!r} in both "
                "import-names and import-namespaces."
            ),
            location=path_location(metadata.pyproject_path),
            requirement=rule.requirement,
            source_line=source_line(str(metadata.pyproject_path), 1),
            label="keep each import owner in only one metadata table",
            labels=dict(rule.labels),
        )
        for item in ambiguous
    )


def _reasoning_tree_import_roots(
    scope: PythonProjectHarnessScope,
    metadata: PythonProjectMetadata,
) -> tuple[Path, ...]:
    roots: list[Path] = []
    seen: set[Path] = set()
    for path in (
        *scope.source_paths,
        *(root.parent for root in metadata.package_roots),
    ):
        _append_path(roots, seen, path)
    if roots:
        return tuple(roots)
    return scope.monitored_paths


def _append_path(paths: list[Path], seen: set[Path], path: Path) -> None:
    key = path.resolve()
    if key in seen:
        return
    seen.add(key)
    paths.append(path)
