"""Model objects for parser-owned Python reasoning-tree facts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .model import PythonModuleReport


@dataclass(frozen=True, slots=True)
class PythonReasoningTreeNode:
    """One import-addressable owner node in a Python project tree."""

    path: str
    namespace: tuple[str, ...]
    kind: str
    parent_namespace: tuple[str, ...] | None
    child_names: tuple[str, ...] = ()
    has_intent_doc: bool = False
    has_public_surface: bool = False
    public_names: tuple[str, ...] = ()
    export_contract_kind: str = "inferred"
    is_valid: bool = True
    effective_code_lines: int = 0

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-compatible representation."""

        return {
            "path": self.path,
            "namespace": list(self.namespace),
            "kind": self.kind,
            "parent_namespace": (
                None if self.parent_namespace is None else list(self.parent_namespace)
            ),
            "child_names": list(self.child_names),
            "has_intent_doc": self.has_intent_doc,
            "has_public_surface": self.has_public_surface,
            "public_names": list(self.public_names),
            "export_contract_kind": self.export_contract_kind,
            "is_valid": self.is_valid,
            "effective_code_lines": self.effective_code_lines,
        }


@dataclass(frozen=True, slots=True)
class PythonReasoningTreeShadow:
    """A module file and package init that define the same import owner."""

    module_path: str
    package_init_path: str
    namespace: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-compatible representation."""

        return {
            "module_path": self.module_path,
            "package_init_path": self.package_init_path,
            "namespace": list(self.namespace),
        }


@dataclass(frozen=True, slots=True)
class PythonReasoningTreeImportEdge:
    """One parser-resolved internal project import edge."""

    importer_path: str
    importer_namespace: tuple[str, ...]
    imported_path: str
    imported_namespace: tuple[str, ...]
    import_name: str
    bound_name: str
    scope: str
    line: int
    column: int
    is_relative: bool = False

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-compatible representation."""

        return {
            "importer_path": self.importer_path,
            "importer_namespace": list(self.importer_namespace),
            "imported_path": self.imported_path,
            "imported_namespace": list(self.imported_namespace),
            "import_name": self.import_name,
            "bound_name": self.bound_name,
            "scope": self.scope,
            "line": self.line,
            "column": self.column,
            "is_relative": self.is_relative,
        }


@dataclass(frozen=True, slots=True)
class PythonReasoningTreeBranch:
    """A package branch that owns multiple immediate child modules."""

    path: str
    namespace: tuple[str, ...]
    child_count: int
    child_names: tuple[str, ...]
    has_intent_doc: bool
    has_public_surface: bool

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-compatible representation."""

        return {
            "path": self.path,
            "namespace": list(self.namespace),
            "child_count": self.child_count,
            "child_names": list(self.child_names),
            "has_intent_doc": self.has_intent_doc,
            "has_public_surface": self.has_public_surface,
        }


@dataclass(frozen=True, slots=True)
class PythonReasoningTreeFacts:
    """Project-level package tree facts derived from parser reports."""

    nodes: tuple[PythonReasoningTreeNode, ...] = ()
    shadowed_module_sources: tuple[PythonReasoningTreeShadow, ...] = ()
    import_edges: tuple[PythonReasoningTreeImportEdge, ...] = ()
    branches: tuple[PythonReasoningTreeBranch, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-compatible representation."""

        return {
            "nodes": [item.to_dict() for item in self.nodes],
            "shadowed_module_sources": [
                item.to_dict() for item in self.shadowed_module_sources
            ],
            "import_edges": [item.to_dict() for item in self.import_edges],
            "branches": [item.to_dict() for item in self.branches],
        }


@dataclass(frozen=True, slots=True)
class PythonReasoningTreeModuleInfo:
    """One parsed module with import-root namespace context."""

    report: PythonModuleReport
    path: str
    namespace: tuple[str, ...]
    is_package_init: bool
