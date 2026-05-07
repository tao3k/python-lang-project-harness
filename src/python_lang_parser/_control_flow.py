"""Parser-owned function control-flow shape collection."""

from __future__ import annotations

import ast
from dataclasses import dataclass

from ._ast_names import unparse
from .model import PythonFunctionControlFlow


def collect_function_control_flow(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> PythonFunctionControlFlow:
    """Return compact control-flow shape facts for one function body."""

    collector = _ControlFlowCollector()
    collector.visit_statements(node.body, nesting_depth=0, loop_depth=0)
    return PythonFunctionControlFlow(
        statement_count=collector.statement_count,
        max_block_statement_count=collector.max_block_statement_count,
        branch_count=collector.branch_count,
        loop_count=collector.loop_count,
        match_count=collector.match_count,
        return_count=collector.return_count,
        terminal_else_count=collector.terminal_else_count,
        max_nesting_depth=collector.max_nesting_depth,
        max_loop_nesting_depth=collector.max_loop_nesting_depth,
        max_literal_dispatch_chain=collector.max_literal_dispatch_chain,
        nested_control_flow_count=collector.nested_control_flow_count,
    )


@dataclass(slots=True)
class _ControlFlowCollector:
    statement_count: int = 0
    max_block_statement_count: int = 0
    branch_count: int = 0
    loop_count: int = 0
    match_count: int = 0
    return_count: int = 0
    terminal_else_count: int = 0
    max_nesting_depth: int = 0
    max_loop_nesting_depth: int = 0
    max_literal_dispatch_chain: int = 0
    nested_control_flow_count: int = 0

    def visit_statements(
        self,
        statements: list[ast.stmt],
        *,
        nesting_depth: int,
        loop_depth: int,
    ) -> None:
        self.max_block_statement_count = max(
            self.max_block_statement_count,
            len(statements),
        )
        for statement in statements:
            self.visit_statement(
                statement,
                nesting_depth=nesting_depth,
                loop_depth=loop_depth,
            )

    def visit_statement(
        self,
        statement: ast.stmt,
        *,
        nesting_depth: int,
        loop_depth: int,
    ) -> None:
        self.statement_count += 1
        if isinstance(statement, ast.If):
            self._visit_if(
                statement,
                nesting_depth=nesting_depth,
                loop_depth=loop_depth,
            )
            return
        if isinstance(statement, ast.For | ast.AsyncFor | ast.While):
            self._visit_loop(
                statement,
                nesting_depth=nesting_depth,
                loop_depth=loop_depth,
            )
            return
        if isinstance(statement, ast.Match):
            self._visit_match(
                statement,
                nesting_depth=nesting_depth,
                loop_depth=loop_depth,
            )
            return
        if isinstance(statement, ast.Try):
            self._visit_try(
                statement,
                nesting_depth=nesting_depth,
                loop_depth=loop_depth,
            )
            return
        if isinstance(statement, ast.With | ast.AsyncWith):
            self._visit_block(
                statement.body,
                nesting_depth=nesting_depth + 1,
                loop_depth=loop_depth,
            )
            return
        if isinstance(statement, ast.Return):
            self.return_count += 1

    def _visit_if(
        self,
        statement: ast.If,
        *,
        nesting_depth: int,
        loop_depth: int,
    ) -> None:
        depth = nesting_depth + 1
        self._record_control_flow(depth)
        self.branch_count += 1
        self.max_literal_dispatch_chain = max(
            self.max_literal_dispatch_chain,
            _literal_dispatch_chain_count(statement),
        )
        if statement.orelse and _body_has_terminal_exit(statement.body):
            self.terminal_else_count += 1
        self.visit_statements(
            statement.body,
            nesting_depth=depth,
            loop_depth=loop_depth,
        )
        if len(statement.orelse) == 1 and isinstance(statement.orelse[0], ast.If):
            self.visit_statement(
                statement.orelse[0],
                nesting_depth=nesting_depth,
                loop_depth=loop_depth,
            )
            return
        self.visit_statements(
            statement.orelse,
            nesting_depth=depth,
            loop_depth=loop_depth,
        )

    def _visit_loop(
        self,
        statement: ast.For | ast.AsyncFor | ast.While,
        *,
        nesting_depth: int,
        loop_depth: int,
    ) -> None:
        depth = nesting_depth + 1
        next_loop_depth = loop_depth + 1
        self._record_control_flow(depth)
        self.loop_count += 1
        self.max_loop_nesting_depth = max(
            self.max_loop_nesting_depth,
            next_loop_depth,
        )
        self.visit_statements(
            statement.body,
            nesting_depth=depth,
            loop_depth=next_loop_depth,
        )
        self.visit_statements(
            statement.orelse,
            nesting_depth=depth,
            loop_depth=next_loop_depth,
        )

    def _visit_match(
        self,
        statement: ast.Match,
        *,
        nesting_depth: int,
        loop_depth: int,
    ) -> None:
        depth = nesting_depth + 1
        self._record_control_flow(depth)
        self.match_count += 1
        self.branch_count += len(statement.cases)
        for case in statement.cases:
            self.visit_statements(
                case.body,
                nesting_depth=depth,
                loop_depth=loop_depth,
            )

    def _visit_try(
        self,
        statement: ast.Try,
        *,
        nesting_depth: int,
        loop_depth: int,
    ) -> None:
        depth = nesting_depth + 1
        self._record_control_flow(depth)
        self.branch_count += len(statement.handlers)
        self.branch_count += 1 if statement.orelse else 0
        self.branch_count += 1 if statement.finalbody else 0
        self.visit_statements(
            statement.body,
            nesting_depth=depth,
            loop_depth=loop_depth,
        )
        for handler in statement.handlers:
            self.visit_statements(
                handler.body,
                nesting_depth=depth,
                loop_depth=loop_depth,
            )
        self.visit_statements(
            statement.orelse,
            nesting_depth=depth,
            loop_depth=loop_depth,
        )
        self.visit_statements(
            statement.finalbody,
            nesting_depth=depth,
            loop_depth=loop_depth,
        )

    def _visit_block(
        self,
        statements: list[ast.stmt],
        *,
        nesting_depth: int,
        loop_depth: int,
    ) -> None:
        self.max_nesting_depth = max(self.max_nesting_depth, nesting_depth)
        self.visit_statements(
            statements,
            nesting_depth=nesting_depth,
            loop_depth=loop_depth,
        )

    def _record_control_flow(self, depth: int) -> None:
        self.max_nesting_depth = max(self.max_nesting_depth, depth)
        if depth >= 3:
            self.nested_control_flow_count += 1


def _body_has_terminal_exit(statements: list[ast.stmt]) -> bool:
    if not statements:
        return False
    return _statement_has_terminal_exit(statements[-1])


def _statement_has_terminal_exit(statement: ast.stmt) -> bool:
    if isinstance(statement, ast.Return | ast.Raise | ast.Break | ast.Continue):
        return True
    if isinstance(statement, ast.If):
        return (
            bool(statement.orelse)
            and _body_has_terminal_exit(statement.body)
            and _body_has_terminal_exit(statement.orelse)
        )
    if isinstance(statement, ast.Match):
        return bool(statement.cases) and all(
            _body_has_terminal_exit(case.body) for case in statement.cases
        )
    return False


def _literal_dispatch_chain_count(statement: ast.If) -> int:
    subject = _literal_dispatch_subject(statement.test)
    if subject is None:
        return 0
    count = 0
    current: ast.If | None = statement
    while current is not None:
        if _literal_dispatch_subject(current.test) != subject:
            break
        count += 1
        current = (
            current.orelse[0]
            if len(current.orelse) == 1 and isinstance(current.orelse[0], ast.If)
            else None
        )
    return count


def _literal_dispatch_subject(expression: ast.expr) -> str | None:
    if not isinstance(expression, ast.Compare):
        return None
    if len(expression.ops) != 1 or len(expression.comparators) != 1:
        return None
    operator = expression.ops[0]
    comparator = expression.comparators[0]
    if isinstance(operator, ast.Eq | ast.Is) and _is_literal_dispatch_value(comparator):
        return unparse(expression.left)
    if isinstance(operator, ast.In) and _is_literal_container(comparator):
        return unparse(expression.left)
    return None


def _is_literal_dispatch_value(expression: ast.expr) -> bool:
    return isinstance(expression, ast.Constant)


def _is_literal_container(expression: ast.expr) -> bool:
    return isinstance(expression, ast.Tuple | ast.Set | ast.List) and all(
        _is_literal_dispatch_value(item) for item in expression.elts
    )
