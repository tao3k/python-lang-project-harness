"""Parser-owned aggregation of native Python loop idiom facts."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field

from ._native_collection_loops import (
    is_manual_predicate_loop_at,
    manual_collection_loop_kind,
    updated_collection_bindings,
)
from ._native_mapping_loops import manual_mapping_loop_kind
from ._native_numeric_loops import (
    is_manual_numeric_sum_loop,
    updated_numeric_accumulator_bindings,
)


@dataclass(frozen=True, slots=True)
class PythonNativeIdiomLoopFacts:
    """Compact parser facts for native-idiom loop opportunities."""

    manual_collection_loop_count: int = 0
    manual_predicate_loop_count: int = 0
    manual_mapping_count_loop_count: int = 0
    manual_mapping_group_loop_count: int = 0
    manual_numeric_sum_loop_count: int = 0


def collect_native_idiom_loop_facts(
    statements: list[ast.stmt],
) -> PythonNativeIdiomLoopFacts:
    """Return native-idiom loop opportunities for one statement block."""

    state = _NativeIdiomLoopState()
    for index in range(len(statements)):
        state.record_statement(statements, index)
    return state.to_facts()


@dataclass(slots=True)
class _NativeIdiomLoopState:
    collection_bindings: dict[str, str] = field(default_factory=dict)
    numeric_accumulators: frozenset[str] = frozenset()
    manual_collection_loop_count: int = 0
    manual_predicate_loop_count: int = 0
    manual_mapping_count_loop_count: int = 0
    manual_mapping_group_loop_count: int = 0
    manual_numeric_sum_loop_count: int = 0

    def record_statement(self, statements: list[ast.stmt], index: int) -> None:
        statement = statements[index]
        self._record_loop(statement)
        self._record_predicate(statements, index)
        self._advance_bindings(statement)

    def to_facts(self) -> PythonNativeIdiomLoopFacts:
        return PythonNativeIdiomLoopFacts(
            manual_collection_loop_count=self.manual_collection_loop_count,
            manual_predicate_loop_count=self.manual_predicate_loop_count,
            manual_mapping_count_loop_count=self.manual_mapping_count_loop_count,
            manual_mapping_group_loop_count=self.manual_mapping_group_loop_count,
            manual_numeric_sum_loop_count=self.manual_numeric_sum_loop_count,
        )

    def _record_loop(self, statement: ast.stmt) -> None:
        collection_bindings = self.collection_bindings
        self.manual_collection_loop_count += int(
            manual_collection_loop_kind(statement, collection_bindings) is not None
        )
        self.manual_numeric_sum_loop_count += int(
            is_manual_numeric_sum_loop(statement, self.numeric_accumulators)
        )
        match manual_mapping_loop_kind(statement, collection_bindings):
            case "count":
                self.manual_mapping_count_loop_count += 1
            case "group":
                self.manual_mapping_group_loop_count += 1
            case _:
                return

    def _record_predicate(self, statements: list[ast.stmt], index: int) -> None:
        self.manual_predicate_loop_count += int(
            is_manual_predicate_loop_at(statements, index)
        )

    def _advance_bindings(self, statement: ast.stmt) -> None:
        self.collection_bindings = updated_collection_bindings(
            self.collection_bindings,
            statement,
        )
        self.numeric_accumulators = updated_numeric_accumulator_bindings(
            self.numeric_accumulators,
            statement,
        )
