"""Rule catalog for native Python syntax and compile diagnostics."""

from __future__ import annotations

from dataclasses import replace

from python_lang_parser import PythonDiagnosticSeverity

from ._model import PythonHarnessRule

SYNTAX_PACK_ID = "python.syntax"
PYTHON_SYNTAX_INVALID = "python.syntax.invalid"
PYTHON_COMPILE_INVALID = "python.compile.invalid"

_RULE_LABELS = {
    "language": "python",
    "domain": "syntax",
}
_RULES = (
    PythonHarnessRule(
        rule_id=PYTHON_SYNTAX_INVALID,
        pack_id=SYNTAX_PACK_ID,
        severity=PythonDiagnosticSeverity.ERROR,
        title="Python source did not parse",
        requirement="Python modules must parse with CPython native syntax before project rules run.",
        labels=dict(_RULE_LABELS),
    ),
    PythonHarnessRule(
        rule_id=PYTHON_COMPILE_INVALID,
        pack_id=SYNTAX_PACK_ID,
        severity=PythonDiagnosticSeverity.ERROR,
        title="Python source did not compile",
        requirement="Python modules must compile through CPython native validation before project rules run.",
        labels=dict(_RULE_LABELS),
    ),
)
_RULE_BY_ID = {rule.rule_id: rule for rule in _RULES}


def python_syntax_rules() -> tuple[PythonHarnessRule, ...]:
    """Return compact metadata for native Python syntax rules."""

    return tuple(replace(rule, labels=dict(rule.labels)) for rule in _RULES)


def syntax_rule(rule_id: str) -> PythonHarnessRule:
    """Return one syntax rule descriptor by stable rule id."""

    return _RULE_BY_ID[rule_id]
