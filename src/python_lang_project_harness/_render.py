"""Compact snapshot rendering for Python harness diagnostics."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from python_lang_parser import PythonDiagnosticSeverity, python_reasoning_tree_facts

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from python_lang_parser import (
        PythonProjectImportName,
        PythonProjectMetadata,
        PythonReasoningTreeImportEdge,
        PythonReasoningTreeNode,
    )

    from ._model import PythonHarnessFinding, PythonHarnessReport


def render_python_lang_harness(
    report: PythonHarnessReport,
    *,
    severities: frozenset[PythonDiagnosticSeverity] | None = None,
    include_advice: bool = True,
) -> str:
    """Render a compact diagnostic report for humans and repair workflows."""

    blocking_findings = report.blocking_findings(severities=severities)
    advice_findings = (
        _deduplicate_advice_findings(
            report.advisory_findings(),
            blocking_findings=blocking_findings,
        )
        if include_advice
        else ()
    )
    if blocking_findings:
        rendered = _render_findings(blocking_findings)
        if advice_findings:
            rendered += "\n[advice]\n" + _render_findings(advice_findings)
        return rendered
    if advice_findings:
        return "[advice]\n" + _render_findings(advice_findings)
    return _render_ok_header(report)


def render_python_lang_harness_json(report: PythonHarnessReport) -> str:
    """Render a structured JSON diagnostic report for tool consumers."""

    return json.dumps(report.to_dict(), separators=(",", ":"), sort_keys=True)


def render_python_lang_harness_advice(report: PythonHarnessReport) -> str:
    """Render non-blocking advisory findings for agent-guided repair."""

    advice_findings = _deduplicate_advice_findings(
        report.advisory_findings(),
        blocking_findings=report.blocking_findings(),
    )
    if not advice_findings:
        return ""
    return _render_findings(advice_findings)


def render_python_reasoning_tree(
    report: PythonHarnessReport,
    *,
    max_nodes: int = 80,
    max_edges: int = 80,
) -> str:
    """Render a compact project reasoning tree for repair-oriented agents."""

    facts = python_reasoning_tree_facts(
        report.modules,
        import_roots=_reasoning_tree_import_roots(report),
        project_root=(
            None if report.project_scope is None else report.project_scope.project_root
        ),
        project_metadata=(
            None
            if report.project_scope is None
            else report.project_scope.project_metadata
        ),
    )
    target = ", ".join(report.root_paths)
    lines = [f"[tree] {target} python"]
    if facts.shadowed_module_sources:
        lines.append("[shadows]")
        for shadow in facts.shadowed_module_sources:
            namespace = ".".join(shadow.namespace)
            lines.append(
                f"- {namespace}: {shadow.module_path} <-> {shadow.package_init_path}"
            )
    if facts.project_metadata is not None:
        lines.extend(_render_reasoning_tree_project_metadata(facts.project_metadata))
    lines.append("[nodes]")
    for node in facts.nodes[:max_nodes]:
        lines.append(_render_reasoning_tree_node(node))
    omitted = len(facts.nodes) - max_nodes
    if omitted > 0:
        lines.append(f"... {omitted} more nodes")
    if facts.import_edges:
        lines.append("[imports]")
        for edge in facts.import_edges[:max_edges]:
            lines.append(_render_reasoning_tree_import_edge(edge))
        omitted_edges = len(facts.import_edges) - max_edges
        if omitted_edges > 0:
            lines.append(f"... {omitted_edges} more imports")
    return "\n".join(lines) + "\n"


def _render_ok_header(report: PythonHarnessReport) -> str:
    target = ", ".join(report.root_paths)
    return (
        f"[ok] {target} python\n"
        f"Files: {report.file_count} Parsed: {report.parsed_count}\n"
    )


def _render_findings(findings: tuple[PythonHarnessFinding, ...]) -> str:
    return (
        "\n\n".join(_render_finding(finding).rstrip("\n") for finding in findings)
        + "\n"
    )


def _render_finding(finding: PythonHarnessFinding) -> str:
    path = finding.location.path or "<memory>"
    line = finding.location.line
    column = finding.location.column
    severity = finding.severity.value.title()
    display_column = column + 1
    rendered = (
        f"[{finding.rule_id}] {severity}: {finding.title}\n"
        f"   ,-[ {path}:{line}:{display_column} ]\n"
    )
    if finding.source_line:
        pointer_column = max(column, 0)
        rendered += f"{line:>2} | {finding.source_line}\n   | {' ' * pointer_column}`- {finding.label}\n"
    else:
        rendered += f"   | {finding.label}\n"
    rendered += f"   |Required: {finding.requirement}\n"
    return rendered


def _reasoning_tree_import_roots(report: PythonHarnessReport) -> tuple[Path | str, ...]:
    if report.project_scope is None:
        return report.root_paths
    if report.project_scope.source_paths:
        return report.project_scope.source_paths
    return report.project_scope.monitored_paths


def _render_reasoning_tree_node(node: PythonReasoningTreeNode) -> str:
    depth = max(len(node.namespace) - 1, 0)
    indent = "  " * depth
    namespace = ".".join(node.namespace) if node.namespace else "<root>"
    flags = [
        node.kind,
        "doc" if node.has_intent_doc else "no-doc",
        "public" if node.has_public_surface else "internal",
    ]
    if node.child_names:
        flags.append("children=" + ",".join(node.child_names))
    export_flag = _render_reasoning_tree_export_flag(node)
    if export_flag is not None:
        flags.append(export_flag)
    if not node.is_valid:
        flags.append("invalid")
    return f"{indent}- {namespace} ({'; '.join(flags)}) {node.path}"


def _render_reasoning_tree_project_metadata(
    project_metadata: PythonProjectMetadata,
) -> list[str]:
    import_names = project_metadata.import_names
    import_namespaces = project_metadata.import_namespaces
    package_roots = project_metadata.package_roots
    scripts = project_metadata.scripts
    entry_points = project_metadata.entry_points
    lines = ["[project]"]
    name = project_metadata.project_name or "<unnamed>"
    requires_python = project_metadata.requires_python or "<any>"
    lines.append(f"- name={name} requires-python={requires_python}")
    if import_names:
        lines.append("- import-names=" + _render_project_import_names(import_names))
    if import_namespaces:
        lines.append(
            "- import-namespaces=" + _render_project_import_names(import_namespaces)
        )
    if package_roots:
        lines.append(
            "- package-roots="
            + _render_compact_name_list(
                tuple(str(path) for path in package_roots),
                max_names=4,
            )
        )
    if scripts:
        lines.append(
            "- scripts="
            + _render_compact_name_list(
                tuple(script.name for script in scripts),
                max_names=6,
            )
        )
    if entry_points:
        lines.append(
            "- entry-points="
            + _render_compact_name_list(
                tuple(f"{entry.group}:{entry.name}" for entry in entry_points),
                max_names=6,
            )
        )
    return lines


def _render_project_import_names(
    import_names: Sequence[PythonProjectImportName],
) -> str:
    names = tuple(
        (import_name.name + (";private" if import_name.is_private else ""))
        for import_name in import_names
    )
    return _render_compact_name_list(names)


def _render_reasoning_tree_export_flag(node: PythonReasoningTreeNode) -> str | None:
    if node.public_names:
        return "exports=" + _render_compact_name_list(node.public_names)
    if node.export_contract_kind == "static":
        return "exports=none"
    if node.export_contract_kind == "dynamic":
        return "exports=dynamic"
    return None


def _render_compact_name_list(names: tuple[str, ...], *, max_names: int = 6) -> str:
    shown = names[:max_names]
    rendered = ",".join(shown)
    omitted = len(names) - len(shown)
    if omitted > 0:
        rendered += f",+{omitted}"
    return rendered


def _render_reasoning_tree_import_edge(edge: PythonReasoningTreeImportEdge) -> str:
    importer = ".".join(edge.importer_namespace)
    imported = ".".join(edge.imported_namespace)
    scope = "module" if edge.scope == "" else edge.scope
    relation = "relative" if edge.is_relative else "absolute"
    return f"- {importer} -> {imported} ({relation}; {scope}; as {edge.bound_name})"


def _deduplicate_advice_findings(
    advice_findings: tuple[PythonHarnessFinding, ...],
    *,
    blocking_findings: tuple[PythonHarnessFinding, ...],
) -> tuple[PythonHarnessFinding, ...]:
    blocking_keys = {_finding_key(finding) for finding in blocking_findings}
    return tuple(
        finding
        for finding in advice_findings
        if _finding_key(finding) not in blocking_keys
    )


def _finding_key(finding: PythonHarnessFinding) -> tuple[str, str | None, int, int]:
    return (
        finding.rule_id,
        finding.location.path,
        finding.location.line,
        finding.location.column,
    )
