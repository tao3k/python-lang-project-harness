"""Python public-name policy helpers shared by parser consumers."""

from __future__ import annotations


def python_name_is_public(name: str) -> bool:
    """Return whether a parser-visible name belongs to public project surface."""

    return bool(name) and not name.startswith(("_", "test_")) and "." not in name


def python_scope_is_public(scope: str) -> bool:
    """Return whether every dotted scope segment is public."""

    return all(python_name_is_public(part) for part in scope.split(".") if part)
