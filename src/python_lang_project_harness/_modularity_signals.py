"""Mixed parser-backed signals for Python modularity rules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from python_lang_parser import python_symbol_is_callable

if TYPE_CHECKING:
    from python_lang_parser import PythonModuleReport, PythonSymbol

MAX_MODULE_EFFECTIVE_CODE_LINES = 220
MAX_MODULE_TOP_LEVEL_ITEMS = 8
MIN_MODULE_RESPONSIBILITY_GROUPS = 3
MIN_MODULE_PUBLIC_SURFACE_ITEMS = 5
MAX_FUNCTION_LINES = 80


@dataclass(frozen=True, slots=True)
class ModuleComplexitySignals:
    """Parser-backed mixed signals used by the module bloat rule."""

    effective_code_lines: int
    top_level_statement_count: int
    responsibility_group_count: int
    public_surface_count: int
    long_function_count: int
    max_function_lines: int
    split_indicators: tuple[str, ...]


def collect_module_complexity_signals(
    report: PythonModuleReport,
) -> ModuleComplexitySignals:
    """Return mixed parser-backed modularity signals for one module."""

    shape = report.shape
    if shape is None:
        return ModuleComplexitySignals(0, 0, 0, 0, 0, 0, ())

    function_spans = tuple(
        _symbol_line_span(symbol)
        for symbol in report.symbols
        if python_symbol_is_callable(symbol)
    )
    long_function_count = sum(span > MAX_FUNCTION_LINES for span in function_spans)
    max_function_lines = max(function_spans, default=0)
    indicators = _split_indicators(
        top_level_statement_count=shape.top_level_statement_count,
        responsibility_group_count=shape.responsibility_group_count,
        public_surface_count=shape.public_surface_count,
        long_function_count=long_function_count,
    )
    return ModuleComplexitySignals(
        effective_code_lines=shape.effective_code_lines,
        top_level_statement_count=shape.top_level_statement_count,
        responsibility_group_count=shape.responsibility_group_count,
        public_surface_count=shape.public_surface_count,
        long_function_count=long_function_count,
        max_function_lines=max_function_lines,
        split_indicators=indicators,
    )


def module_needs_split(signals: ModuleComplexitySignals) -> bool:
    """Return whether mixed signals justify a module-split finding."""

    if signals.effective_code_lines < MAX_MODULE_EFFECTIVE_CODE_LINES:
        return False
    if signals.long_function_count:
        return True
    return len(signals.split_indicators) >= 2


def _split_indicators(
    *,
    top_level_statement_count: int,
    responsibility_group_count: int,
    public_surface_count: int,
    long_function_count: int,
) -> tuple[str, ...]:
    indicators: list[str] = []
    if top_level_statement_count >= MAX_MODULE_TOP_LEVEL_ITEMS:
        indicators.append("many top-level items")
    if responsibility_group_count >= MIN_MODULE_RESPONSIBILITY_GROUPS:
        indicators.append("mixed responsibility groups")
    if public_surface_count >= MIN_MODULE_PUBLIC_SURFACE_ITEMS:
        indicators.append("wide public surface")
    if long_function_count:
        indicators.append("long function spans")
    return tuple(indicators)


def _symbol_line_span(symbol: PythonSymbol) -> int:
    if symbol.end_line is None:
        return 0
    return max(1, symbol.end_line - symbol.location.line + 1)
