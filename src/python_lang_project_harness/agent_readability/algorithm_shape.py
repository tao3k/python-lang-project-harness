"""Agent-facing algorithm-shape advice from parser-owned function facts."""

from __future__ import annotations

from typing import TYPE_CHECKING

from python_lang_parser import (
    python_symbol_is_public_callable_boundary,
    python_symbol_is_public_class,
)

from .._agent_policy_catalog import PY_AGENT_R009, agent_policy_rule
from .._model import PythonHarnessFinding

if TYPE_CHECKING:
    from python_lang_parser import (
        PythonFunctionControlFlow,
        PythonModuleReport,
        PythonSymbol,
    )


def agent_algorithm_shape_findings(
    report: PythonModuleReport,
    pack_id: str,
) -> tuple[PythonHarnessFinding, ...]:
    """Return machine-readability advice for public algorithm boundaries."""

    findings: list[PythonHarnessFinding] = []
    rule = agent_policy_rule(PY_AGENT_R009)
    public_class_scopes = _public_class_scopes(report)
    for symbol in report.symbols:
        control_flow = symbol.control_flow
        if (
            not _is_agent_algorithm_boundary(
                symbol,
                public_class_scopes=public_class_scopes,
            )
            or control_flow is None
        ):
            continue
        profile = _agent_algorithm_profile(control_flow)
        if not profile:
            continue
        findings.append(
            PythonHarnessFinding(
                rule_id=rule.rule_id,
                pack_id=pack_id,
                severity=rule.severity,
                title=rule.title,
                summary=_summary(symbol, control_flow),
                location=symbol.location,
                requirement=f"{rule.requirement} Signals: {', '.join(profile)}.",
                source_line=report.source_line(symbol.location.line),
                label="make this algorithm shape explicit",
                labels=dict(rule.labels),
            )
        )
    return tuple(findings)


def _is_agent_algorithm_boundary(
    symbol: PythonSymbol,
    *,
    public_class_scopes: frozenset[str],
) -> bool:
    return python_symbol_is_public_callable_boundary(
        symbol,
        public_class_scopes=public_class_scopes,
    )


def _public_class_scopes(report: PythonModuleReport) -> frozenset[str]:
    return frozenset(
        symbol.qualified_name
        for symbol in report.symbols
        if python_symbol_is_public_class(symbol)
    )


def _agent_algorithm_profile(
    control_flow: PythonFunctionControlFlow,
) -> tuple[str, ...]:
    indicators: list[str] = []
    if control_flow.max_nesting_depth >= 4:
        indicators.append("deep control-flow nesting")
    if control_flow.max_loop_nesting_depth >= 2 and control_flow.branch_count >= 3:
        indicators.append("nested loops mixed with branches")
    if control_flow.max_literal_dispatch_chain >= 4 and control_flow.match_count == 0:
        indicators.append("literal dispatch chain without match/case")
    if control_flow.terminal_else_count >= 2 and control_flow.max_nesting_depth >= 3:
        indicators.append("else blocks after terminal branches")
    if control_flow.nested_control_flow_count >= 4:
        indicators.append("many nested control-flow blocks")
    return tuple(indicators)


def _summary(
    symbol: PythonSymbol,
    control_flow: PythonFunctionControlFlow,
) -> str:
    return (
        f"{symbol.qualified_name} has nesting depth "
        f"{control_flow.max_nesting_depth}, loop nesting "
        f"{control_flow.max_loop_nesting_depth}, "
        f"{control_flow.branch_count} branches, and "
        f"literal dispatch chain {control_flow.max_literal_dispatch_chain}."
    )
