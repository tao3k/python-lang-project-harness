from __future__ import annotations

from pathlib import Path

from python_lang_parser import parse_python_source

_PROJECT_ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "pyproject.toml").exists() and (parent / "src").exists()
)


def test_parse_python_source_collects_function_control_flow_shape() -> None:
    report = parse_python_source(
        '''
"""Control-flow fixture."""


def classify(kind: str, rows: list[object]) -> int:
    for row in rows:
        if row:
            if kind == "alpha":
                return 1
            elif kind == "beta":
                return 2
            elif kind == "gamma":
                return 3
            elif kind == "delta":
                return 4
            else:
                return 0
    return -1
''',
        path="control_flow.py",
    )

    control_flow = report.symbols[0].control_flow

    assert control_flow is not None
    assert control_flow.statement_count == 12
    assert control_flow.max_block_statement_count == 2
    assert control_flow.branch_count == 5
    assert control_flow.loop_count == 1
    assert control_flow.return_count == 6
    assert control_flow.terminal_else_count == 4
    assert control_flow.max_nesting_depth == 3
    assert control_flow.max_loop_nesting_depth == 1
    assert control_flow.max_literal_dispatch_chain == 4


def test_control_flow_collector_avoids_module_wide_ast_walks() -> None:
    source = (
        _PROJECT_ROOT / "src" / "python_lang_parser" / "_control_flow.py"
    ).read_text(encoding="utf-8")

    assert "ast.walk" not in source
    assert "generic_visit" not in source
