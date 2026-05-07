"""Parser-owned aggregation of native Python loop idiom facts."""

from __future__ import annotations

import ast
from dataclasses import dataclass

from ._native_collection_loops import (
    collection_bindings,
    is_manual_predicate_loop_at,
    manual_collection_loop_kind,
)
from ._native_mapping_loops import manual_mapping_loop_kind
from ._native_numeric_loops import (
    is_manual_numeric_sum_loop,
    numeric_accumulator_bindings,
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

    bindings = collection_bindings(statements)
    accumulator_names = numeric_accumulator_bindings(statements)
    mapping_loop_kinds = tuple(
        kind
        for statement in statements
        if (kind := manual_mapping_loop_kind(statement, bindings)) is not None
    )
    return PythonNativeIdiomLoopFacts(
        manual_collection_loop_count=sum(
            1
            for statement in statements
            if manual_collection_loop_kind(statement, bindings)
        ),
        manual_predicate_loop_count=sum(
            1
            for index in range(len(statements))
            if is_manual_predicate_loop_at(statements, index)
        ),
        manual_mapping_count_loop_count=mapping_loop_kinds.count("count"),
        manual_mapping_group_loop_count=mapping_loop_kinds.count("group"),
        manual_numeric_sum_loop_count=sum(
            1
            for statement in statements
            if is_manual_numeric_sum_loop(statement, accumulator_names)
        ),
    )
