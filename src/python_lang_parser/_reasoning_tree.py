"""Parser-owned Python reasoning-tree facts for project harness consumers."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ._module_identity import (
    python_module_is_package_init,
    python_module_namespace_parts,
)
from ._module_policy import python_module_has_public_surface
from ._reasoning_tree_imports import python_reasoning_tree_import_edges
from ._reasoning_tree_model import (
    PythonReasoningTreeBranch,
    PythonReasoningTreeFacts,
    PythonReasoningTreeImportEdge,
    PythonReasoningTreeModuleInfo,
    PythonReasoningTreeNode,
    PythonReasoningTreeShadow,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .model import PythonModuleReport

__all__ = [
    "PythonReasoningTreeBranch",
    "PythonReasoningTreeFacts",
    "PythonReasoningTreeImportEdge",
    "PythonReasoningTreeNode",
    "PythonReasoningTreeShadow",
    "python_reasoning_tree_facts",
]


def python_reasoning_tree_facts(
    modules: Sequence[PythonModuleReport],
    *,
    import_roots: Sequence[str | Path] = (),
    project_root: str | Path | None = None,
) -> PythonReasoningTreeFacts:
    """Return package-tree facts that help agents traverse Python projects."""

    module_infos = tuple(
        _module_info(
            report,
            import_roots=import_roots,
            project_root=project_root,
        )
        for report in modules
        if report.path is not None
    )
    return PythonReasoningTreeFacts(
        nodes=_nodes(module_infos),
        shadowed_module_sources=_shadowed_module_sources(module_infos),
        import_edges=python_reasoning_tree_import_edges(module_infos),
        branches=_branches(module_infos),
    )


def _module_info(
    report: PythonModuleReport,
    *,
    import_roots: Sequence[str | Path],
    project_root: str | Path | None,
) -> PythonReasoningTreeModuleInfo:
    path = report.path or ""
    return PythonReasoningTreeModuleInfo(
        report=report,
        path=path,
        namespace=python_module_namespace_parts(
            path,
            import_roots=import_roots,
            project_root=project_root,
        ),
        is_package_init=python_module_is_package_init(path),
    )


def _shadowed_module_sources(
    modules: tuple[PythonReasoningTreeModuleInfo, ...],
) -> tuple[PythonReasoningTreeShadow, ...]:
    package_inits = {
        module.namespace: module
        for module in modules
        if module.is_package_init and module.namespace
    }
    shadows: list[PythonReasoningTreeShadow] = []
    for module in modules:
        if module.is_package_init or not module.namespace:
            continue
        package_init = package_inits.get(module.namespace)
        if package_init is None:
            continue
        shadows.append(
            PythonReasoningTreeShadow(
                module_path=module.path,
                package_init_path=package_init.path,
                namespace=module.namespace,
            )
        )
    return tuple(sorted(shadows, key=lambda item: item.module_path))


def _nodes(
    modules: tuple[PythonReasoningTreeModuleInfo, ...],
) -> tuple[PythonReasoningTreeNode, ...]:
    child_names_by_namespace = _child_names_by_namespace(modules)
    nodes: list[PythonReasoningTreeNode] = []
    for module in modules:
        parent_namespace = None if len(module.namespace) < 2 else module.namespace[:-1]
        shape = module.report.shape
        nodes.append(
            PythonReasoningTreeNode(
                path=module.path,
                namespace=module.namespace,
                kind="package" if module.is_package_init else "module",
                parent_namespace=parent_namespace,
                child_names=child_names_by_namespace.get(module.namespace, ()),
                has_intent_doc=module.report.module_docstring is not None,
                has_public_surface=python_module_has_public_surface(module.report),
                public_names=module.report.export_candidates,
                export_contract_kind=module.report.export_contract.kind.value,
                is_valid=module.report.is_valid,
                effective_code_lines=0 if shape is None else shape.effective_code_lines,
            )
        )
    return tuple(sorted(nodes, key=lambda item: (item.namespace, item.path)))


def _branches(
    modules: tuple[PythonReasoningTreeModuleInfo, ...],
) -> tuple[PythonReasoningTreeBranch, ...]:
    package_modules = tuple(
        module for module in modules if module.is_package_init and module.namespace
    )
    branches: list[PythonReasoningTreeBranch] = []
    child_names_by_namespace = _child_names_by_namespace(modules)
    for package_module in package_modules:
        child_names = child_names_by_namespace.get(package_module.namespace, ())
        child_count = len(child_names)
        if child_count < 2:
            continue
        branches.append(
            PythonReasoningTreeBranch(
                path=package_module.path,
                namespace=package_module.namespace,
                child_count=child_count,
                child_names=child_names,
                has_intent_doc=package_module.report.module_docstring is not None,
                has_public_surface=python_module_has_public_surface(
                    package_module.report
                ),
            )
        )
    return tuple(sorted(branches, key=lambda item: item.path))


def _child_names_by_namespace(
    modules: tuple[PythonReasoningTreeModuleInfo, ...],
) -> dict[tuple[str, ...], tuple[str, ...]]:
    children: dict[tuple[str, ...], set[str]] = {}
    namespaces = {module.namespace for module in modules}
    for namespace in namespaces:
        if len(namespace) < 2:
            continue
        parent = namespace[:-1]
        children.setdefault(parent, set()).add(namespace[-1])
        for index in range(1, len(namespace) - 1):
            branch = namespace[:index]
            children.setdefault(branch, set()).add(namespace[index])
    return {
        namespace: tuple(sorted(child_names))
        for namespace, child_names in children.items()
    }
