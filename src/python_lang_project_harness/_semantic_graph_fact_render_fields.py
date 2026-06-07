"""Field payload helpers for Python semantic graph rendering."""

from __future__ import annotations

from typing import Any

from ._semantic_graph_fact_model import FieldFact


def field_fact(fact: FieldFact, family: str | None) -> dict[str, Any]:
    return {
        "ownerKind": "class",
        "name": fact.field_name,
        "ownerPath": fact.path,
        "access": access_modes(family),
    }


def type_fact(fact: FieldFact) -> dict[str, str]:
    args = collection_type_args(fact.type_value)
    rendered: dict[str, str] = {"name": fact.type_value}
    if collection_family(fact.collection_kind) == "map":
        if args:
            rendered["key"] = args[0]
        if len(args) > 1:
            rendered["value"] = args[1]
    elif args:
        rendered["element"] = args[0]
    return rendered


def collection_fact(fact: FieldFact) -> dict[str, Any]:
    family = collection_family(fact.collection_kind)
    rendered: dict[str, Any] = {
        "family": family,
        "impl": fact.collection_kind,
        "mutation": mutation_modes(family),
    }
    args = collection_type_args(fact.type_value)
    if family == "map":
        if args:
            rendered["keyType"] = args[0]
        if len(args) > 1:
            rendered["valueType"] = args[1]
    elif args:
        rendered["elementType"] = args[0]
    return rendered


def collection_family(collection_kind: str | None) -> str | None:
    if collection_kind in {"list", "tuple"}:
        return "sequence"
    if collection_kind == "dict":
        return "map"
    if collection_kind == "set":
        return "set"
    return None


def access_modes(family: str | None) -> list[str]:
    if family == "map":
        return ["read", "write", "validate"]
    return ["read", "append", "validate"]


def mutation_modes(family: str | None) -> list[str]:
    if family == "map":
        return ["insert", "remove", "update"]
    if family == "set":
        return ["insert", "remove"]
    return ["append", "remove"]


def collection_type_args(type_value: str) -> list[str]:
    if "[" not in type_value or not type_value.endswith("]"):
        return []
    return [
        part.strip()
        for part in type_value.split("[", 1)[1].removesuffix("]").split(",")
        if part.strip()
    ]
