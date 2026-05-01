"""Python-native AST-backed source parser for modern Python projects."""

from __future__ import annotations

from ._module_identity import (
    python_module_is_package_init,
    python_module_name_from_path,
    python_module_namespace_parts,
)
from ._module_policy import (
    python_module_has_public_surface,
    python_module_has_public_symbol_surface,
)
from ._name_policy import python_name_is_public, python_scope_is_public
from ._symbol_policy import (
    python_assignment_is_public_top_level,
    python_symbol_is_callable,
    python_symbol_is_class,
    python_symbol_is_public_callable,
    python_symbol_is_public_callable_boundary,
    python_symbol_is_public_class,
    python_symbol_is_public_top_level,
    python_symbol_is_test_function,
)
from ._version import __version__
from .model import (
    PythonAssignmentTarget,
    PythonCall,
    PythonCallEffect,
    PythonDiagnostic,
    PythonDiagnosticSeverity,
    PythonExportContract,
    PythonExportContractKind,
    PythonImport,
    PythonModuleReport,
    PythonModuleShape,
    PythonNameBinding,
    PythonReference,
    PythonReferenceKind,
    PythonScope,
    PythonSymbol,
    PythonSymbolKind,
    SourceLocation,
)
from .parser import parse_python_file, parse_python_source

__all__ = [
    "PythonAssignmentTarget",
    "PythonCall",
    "PythonCallEffect",
    "PythonDiagnostic",
    "PythonDiagnosticSeverity",
    "PythonExportContract",
    "PythonExportContractKind",
    "PythonImport",
    "PythonModuleReport",
    "PythonModuleShape",
    "PythonNameBinding",
    "PythonReference",
    "PythonReferenceKind",
    "PythonScope",
    "PythonSymbol",
    "PythonSymbolKind",
    "SourceLocation",
    "__version__",
    "parse_python_file",
    "parse_python_source",
    "python_module_is_package_init",
    "python_module_has_public_surface",
    "python_module_has_public_symbol_surface",
    "python_module_name_from_path",
    "python_module_namespace_parts",
    "python_name_is_public",
    "python_scope_is_public",
    "python_assignment_is_public_top_level",
    "python_symbol_is_callable",
    "python_symbol_is_class",
    "python_symbol_is_public_callable",
    "python_symbol_is_public_callable_boundary",
    "python_symbol_is_public_class",
    "python_symbol_is_public_top_level",
    "python_symbol_is_test_function",
]
