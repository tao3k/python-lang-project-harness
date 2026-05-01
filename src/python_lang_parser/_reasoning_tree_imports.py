"""Internal import-edge resolution for Python reasoning-tree facts."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ._reasoning_tree_model import (
    PythonReasoningTreeImportEdge,
    PythonReasoningTreeModuleInfo,
)

if TYPE_CHECKING:
    from .model import PythonImport


def python_reasoning_tree_import_edges(
    modules: tuple[PythonReasoningTreeModuleInfo, ...],
) -> tuple[PythonReasoningTreeImportEdge, ...]:
    """Return parser-resolved import edges inside one project tree."""

    namespaces = {module.namespace for module in modules if module.namespace}
    modules_by_namespace = _modules_by_namespace(modules)
    edges: list[PythonReasoningTreeImportEdge] = []
    seen: set[tuple[str, tuple[str, ...], str, str, int, int]] = set()
    for module in modules:
        if not module.namespace:
            continue
        for import_record in module.report.imports:
            for import_name, bound_name, imported_namespace in _resolved_imports(
                module,
                import_record,
                namespaces=namespaces,
            ):
                if imported_namespace == module.namespace:
                    continue
                imported_module = modules_by_namespace.get(imported_namespace)
                if imported_module is None:
                    continue
                key = (
                    module.path,
                    imported_namespace,
                    import_name,
                    import_record.scope,
                    import_record.location.line,
                    import_record.location.column,
                )
                if key in seen:
                    continue
                seen.add(key)
                edges.append(
                    PythonReasoningTreeImportEdge(
                        importer_path=module.path,
                        importer_namespace=module.namespace,
                        imported_path=imported_module.path,
                        imported_namespace=imported_namespace,
                        import_name=import_name,
                        bound_name=bound_name,
                        scope=import_record.scope,
                        line=import_record.location.line,
                        column=import_record.location.column,
                        is_relative=import_record.level > 0,
                    )
                )
    return tuple(sorted(edges, key=lambda item: (item.importer_path, item.line)))


def _resolved_imports(
    module: PythonReasoningTreeModuleInfo,
    import_record: PythonImport,
    *,
    namespaces: set[tuple[str, ...]],
) -> tuple[tuple[str, str, tuple[str, ...]], ...]:
    source_names = import_record.source_names or import_record.names
    resolved: list[tuple[str, str, tuple[str, ...]]] = []
    if import_record.module is None:
        for index, source_name in enumerate(source_names):
            imported_namespace = _longest_known_namespace(
                _namespace_parts(source_name),
                namespaces,
            )
            if imported_namespace is None:
                continue
            resolved.append(
                (
                    source_name,
                    _name_at(import_record.names, index, source_name),
                    imported_namespace,
                )
            )
        return tuple(resolved)

    base_namespace = _import_from_base_namespace(module, import_record)
    for index, source_name in enumerate(source_names):
        imported_namespace = (
            base_namespace
            if source_name == "*"
            else _best_from_import_namespace(base_namespace, source_name, namespaces)
        )
        if imported_namespace is None:
            continue
        resolved.append(
            (
                source_name,
                _name_at(import_record.names, index, source_name),
                imported_namespace,
            )
        )
    return tuple(resolved)


def _import_from_base_namespace(
    module: PythonReasoningTreeModuleInfo,
    import_record: PythonImport,
) -> tuple[str, ...]:
    module_parts = _namespace_parts(import_record.module or "")
    if import_record.level == 0:
        return module_parts

    package_namespace = (
        module.namespace if module.is_package_init else module.namespace[:-1]
    )
    keep_count = max(len(package_namespace) - import_record.level + 1, 0)
    return (*package_namespace[:keep_count], *module_parts)


def _best_from_import_namespace(
    base_namespace: tuple[str, ...],
    source_name: str,
    namespaces: set[tuple[str, ...]],
) -> tuple[str, ...] | None:
    module_candidate = (*base_namespace, *_namespace_parts(source_name))
    if module_candidate in namespaces:
        return module_candidate
    if base_namespace in namespaces:
        return base_namespace
    return _longest_known_namespace(module_candidate, namespaces)


def _longest_known_namespace(
    namespace: tuple[str, ...],
    namespaces: set[tuple[str, ...]],
) -> tuple[str, ...] | None:
    for end_index in range(len(namespace), 0, -1):
        candidate = namespace[:end_index]
        if candidate in namespaces:
            return candidate
    return None


def _modules_by_namespace(
    modules: tuple[PythonReasoningTreeModuleInfo, ...],
) -> dict[tuple[str, ...], PythonReasoningTreeModuleInfo]:
    selected: dict[tuple[str, ...], PythonReasoningTreeModuleInfo] = {}
    for module in sorted(
        modules, key=lambda item: (not item.is_package_init, item.path)
    ):
        if not module.namespace:
            continue
        selected.setdefault(module.namespace, module)
    return selected


def _namespace_parts(value: str) -> tuple[str, ...]:
    return tuple(part for part in value.split(".") if part)


def _name_at(names: tuple[str, ...], index: int, default: str) -> str:
    try:
        return names[index]
    except IndexError:
        return default
