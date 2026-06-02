"""Hook query option helpers for the Python harness CLI."""

from __future__ import annotations

from collections.abc import Sequence


def normalize_query_surfaces(value: str | None) -> tuple[tuple[str, ...], str | None]:
    """Normalize shared hook query surfaces into py-harness search pipes."""
    if value is None:
        return (), "--surface requires owner,tests style surfaces"
    surfaces = tuple(surface.strip() for surface in value.split(",") if surface.strip())
    if not surfaces:
        return (), "--surface requires at least one surface"
    pipes: list[str] = []
    for surface in surfaces:
        pipe = "owner" if surface == "owners" else surface
        if pipe not in {"owner", "tests", "items"}:
            return (), f"unknown query surface: {surface}"
        pipes.append(pipe)
    return tuple(pipes), None


def normalize_query_view(value: str | None) -> tuple[str | None, str | None]:
    """Validate the shared hook query view flag."""
    if value not in {"graph", "hits", "both", "seeds"}:
        return None, "--view requires graph, hits, both, or seeds"
    return value, None


def is_broad_hook_query(
    from_hook: str | None,
    selector: str | None,
    terms: Sequence[str],
) -> bool:
    """Return whether hook query args should fan into semantic search."""
    return (
        from_hook == "direct-source-read"
        and selector is not None
        and bool(terms)
        and _selector_has_glob(selector)
    )


def _selector_has_glob(selector: str) -> bool:
    return any(marker in selector for marker in ("*", "?", "[", "]", "{", "}"))
