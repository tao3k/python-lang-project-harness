"""Parser-owned class-shape facts for Agent visual anchors."""

from __future__ import annotations

import ast

from ._ast_names import iter_assignment_target_nodes, qualified_expr_name
from ._name_policy import python_name_is_public
from ._symbol_model import PythonClassShape

_DATACLASS_DECORATORS = frozenset(
    {
        "attr.dataclass",
        "attr.s",
        "attrs.define",
        "attrs.frozen",
        "dataclass",
        "dataclasses.dataclass",
    }
)
_ENUM_BASES = frozenset(
    {
        "Enum",
        "Flag",
        "IntEnum",
        "IntFlag",
        "StrEnum",
        "enum.Enum",
        "enum.Flag",
        "enum.IntEnum",
        "enum.IntFlag",
        "enum.StrEnum",
    }
)
_MODEL_BASES = frozenset(
    {
        "BaseModel",
        "pydantic.BaseModel",
    }
)
_NAMED_TUPLE_BASES = frozenset({"NamedTuple", "typing.NamedTuple"})
_PROTOCOL_BASES = frozenset({"Protocol", "typing.Protocol"})
_TYPED_DICT_BASES = frozenset({"TypedDict", "typing.TypedDict"})


def collect_class_shape(node: ast.ClassDef) -> PythonClassShape:
    """Return parser-visible data/type shape facts for one class."""

    decorators = frozenset(_expression_names(node.decorator_list))
    bases = frozenset(_expression_names(node.bases))
    methods = tuple(_class_methods(node))
    init_fields = _init_self_field_names(methods)
    return PythonClassShape(
        annotated_field_count=_annotated_field_count(node),
        instance_field_count=len(frozenset(init_fields)),
        init_self_assignment_count=len(init_fields),
        method_count=len(methods),
        public_method_count=sum(_method_is_public(method) for method in methods),
        dunder_method_count=sum(_method_is_dunder(method) for method in methods),
        has_dataclass_anchor=bool(decorators & _DATACLASS_DECORATORS),
        has_enum_anchor=bool(bases & _ENUM_BASES),
        has_protocol_anchor=bool(bases & _PROTOCOL_BASES),
        has_typed_dict_anchor=bool(bases & _TYPED_DICT_BASES),
        has_named_tuple_anchor=bool(bases & _NAMED_TUPLE_BASES),
        has_model_anchor=bool(bases & _MODEL_BASES),
    )


def _expression_names(expressions: list[ast.expr]) -> tuple[str, ...]:
    return tuple(qualified_expr_name(expression) for expression in expressions)


def _class_methods(
    node: ast.ClassDef,
) -> tuple[ast.FunctionDef | ast.AsyncFunctionDef, ...]:
    return tuple(
        item
        for item in node.body
        if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef)
    )


def _annotated_field_count(node: ast.ClassDef) -> int:
    return sum(
        isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
        for item in node.body
    )


def _init_self_field_names(
    methods: tuple[ast.FunctionDef | ast.AsyncFunctionDef, ...],
) -> tuple[str, ...]:
    init_method = next(
        (method for method in methods if method.name == "__init__"), None
    )
    if init_method is None:
        return ()
    return tuple(
        field_name
        for statement in ast.walk(init_method)
        for field_name in _self_assignment_field_names(statement)
    )


def _self_assignment_field_names(statement: ast.AST) -> tuple[str, ...]:
    targets = _assignment_targets(statement)
    return tuple(
        field_name
        for target in targets
        if (field_name := _self_field_name(target)) is not None
    )


def _assignment_targets(statement: ast.AST) -> tuple[ast.AST, ...]:
    match statement:
        case ast.Assign(targets=targets):
            return tuple(
                target_node
                for target in targets
                for target_node in iter_assignment_target_nodes(target)
            )
        case ast.AnnAssign(target=target):
            return iter_assignment_target_nodes(target)
        case _:
            return ()


def _self_field_name(target: ast.AST) -> str | None:
    match target:
        case ast.Attribute(value=ast.Name(id="self"), attr=name):
            return name
        case _:
            return None


def _method_is_public(method: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return python_name_is_public(method.name)


def _method_is_dunder(method: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return method.name.startswith("__") and method.name.endswith("__")
