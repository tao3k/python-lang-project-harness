"""Python module surface helpers shared by parser consumers."""

from __future__ import annotations

from .model import PythonModuleReport


def python_module_has_public_symbol_surface(report: PythonModuleReport) -> bool:
    """Return whether a module exposes parser-recognized public symbols."""

    return report.shape is not None and report.shape.public_symbol_count > 0


def python_module_has_public_surface(report: PythonModuleReport) -> bool:
    """Return whether a module exposes parser-recognized public surface."""

    if report.export_candidates:
        return True
    return report.shape is not None and report.shape.has_public_surface
