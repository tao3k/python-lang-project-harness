"""Compact project namespace index for agent-oriented rules."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from python_lang_parser import (
    python_assignment_is_public_top_level,
    python_module_name_from_path,
    python_symbol_is_callable,
    python_symbol_is_class,
    python_symbol_is_public_top_level,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from python_lang_parser import PythonModuleReport, PythonSymbol, SourceLocation


class AgentNamespaceSurface(StrEnum):
    """Public namespace surface categories used by agent policy rules."""

    CALLABLE = "callable"
    TYPE = "type"
    VALUE = "value"


@dataclass(frozen=True, slots=True)
class AgentNamespaceItem:
    """One parser-backed public namespace item."""

    name: str
    surface: AgentNamespaceSurface
    module_path: str | None
    module_name: str
    location: SourceLocation
    source_line: str | None = None


def collect_agent_namespace_items(
    modules: Sequence[PythonModuleReport],
) -> tuple[AgentNamespaceItem, ...]:
    """Return project-level namespace items from parser report facts."""

    items: list[AgentNamespaceItem] = []
    for report in modules:
        if not report.is_valid:
            continue
        items.extend(_symbol_namespace_items(report))
        items.extend(_assignment_namespace_items(report))
    return tuple(items)


def _symbol_namespace_items(
    report: PythonModuleReport,
) -> tuple[AgentNamespaceItem, ...]:
    items: list[AgentNamespaceItem] = []
    for symbol in report.symbols:
        if not python_symbol_is_public_top_level(symbol):
            continue
        surface = _symbol_surface(symbol)
        if surface is None:
            continue
        items.append(
            AgentNamespaceItem(
                name=symbol.name,
                surface=surface,
                module_path=report.path,
                module_name=_module_name(report),
                location=symbol.location,
                source_line=report.source_line(symbol.location.line),
            )
        )
    return tuple(items)


def _assignment_namespace_items(
    report: PythonModuleReport,
) -> tuple[AgentNamespaceItem, ...]:
    items: list[AgentNamespaceItem] = []
    for assignment in report.assignments:
        if not python_assignment_is_public_top_level(assignment):
            continue
        items.append(
            AgentNamespaceItem(
                name=assignment.name,
                surface=AgentNamespaceSurface.VALUE,
                module_path=report.path,
                module_name=_module_name(report),
                location=assignment.location,
                source_line=report.source_line(assignment.location.line),
            )
        )
    return tuple(items)


def _symbol_surface(symbol: PythonSymbol) -> AgentNamespaceSurface | None:
    if python_symbol_is_callable(symbol):
        return AgentNamespaceSurface.CALLABLE
    if python_symbol_is_class(symbol):
        return AgentNamespaceSurface.TYPE
    return None


def _module_name(report: PythonModuleReport) -> str:
    if report.path is None:
        return "<memory>"
    return python_module_name_from_path(report.path)
