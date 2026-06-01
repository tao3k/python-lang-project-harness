"""Fast candidate-file pruning for Python semantic text search."""

from __future__ import annotations

import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from ._semantic_search_prefilter_rank import (
    MAX_PREFILTER_FILES_PER_TERM,
    MAX_PREFILTER_FILES_TOTAL,
    path_matches,
    path_rank,
    ranked_capped_matches,
    ranked_term_matches,
)
from ._semantic_search_prefilter_tools import (
    list_python_files,
    source_match_scores_by_term,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

MIN_PREFILTER_FILES = 128


@dataclass(frozen=True, slots=True)
class PythonSearchPrefilterResult:
    """Files selected before parser-owned fact extraction."""

    paths: tuple[Path, ...]
    total_files: int
    term_capped_files: int
    matched_files: int
    elapsed_ms: int
    tool: str
    reason: str
    query_terms: int
    source_search_passes: int

    def runtime_cost(self) -> dict[str, object]:
        """Return schema-owned runtime-cost metadata for the search packet."""

        return {
            "cacheStatus": "disabled",
            "elapsedMs": self.elapsed_ms,
            "sourceFilesParsed": self.matched_files,
            "reason": self.reason,
            "fields": {
                "prefilterTool": self.tool,
                "candidateFiles": self.total_files,
                "minCandidateFiles": MIN_PREFILTER_FILES,
                "termCappedFiles": self.term_capped_files,
                "matchedFiles": self.matched_files,
                "maxFilesPerTerm": MAX_PREFILTER_FILES_PER_TERM,
                "maxFilesTotal": MAX_PREFILTER_FILES_TOTAL,
                "mode": "text-query-prefilter",
                "queryTerms": self.query_terms,
                "sourceSearchPasses": self.source_search_passes,
            },
        }


def prefilter_python_text_search_paths(
    project_root: Path,
    query_terms: Sequence[str],
    *,
    owner_path: str | None = None,
) -> PythonSearchPrefilterResult | None:
    """Return parser input files preselected by path and source text."""

    terms = _normalized_terms(query_terms)
    rg = shutil.which("rg")
    if rg is None or (not terms and owner_path is None):
        return None
    return _prefilter_with_rg(
        project_root,
        rg,
        terms,
        owner_path=owner_path,
    )


def _prefilter_with_rg(
    project_root: Path,
    rg: str,
    terms: tuple[str, ...],
    *,
    owner_path: str | None,
) -> PythonSearchPrefilterResult | None:
    started = time.perf_counter()
    all_python_files = list_python_files(project_root)
    if len(all_python_files) <= MIN_PREFILTER_FILES:
        return None
    source_scores_by_term = source_match_scores_by_term(project_root, rg, terms)
    term_capped = _term_capped_matches(
        project_root,
        all_python_files,
        terms,
        source_scores_by_term,
    )
    selected = _selected_paths(project_root, term_capped, terms, owner_path)
    elapsed_ms = round((time.perf_counter() - started) * 1000)
    return PythonSearchPrefilterResult(
        paths=selected,
        total_files=len(all_python_files),
        term_capped_files=len(set(term_capped)),
        matched_files=len(selected),
        elapsed_ms=elapsed_ms,
        tool="fd+rg" if _fd_available() else "rg",
        reason="rg/fd prefilter selected parser input files for text query",
        query_terms=len(terms),
        source_search_passes=1 if terms else 0,
    )


def _term_capped_matches(
    project_root: Path,
    all_python_files: tuple[Path, ...],
    terms: tuple[str, ...],
    source_scores_by_term: dict[str, dict[Path, int]],
) -> tuple[Path, ...]:
    matched: list[Path] = []
    for term in terms:
        term_matches = ranked_term_matches(
            project_root,
            term,
            path_matches(project_root, all_python_files, (term,)),
            source_scores_by_term.get(term, {}),
        )
        matched.extend(
            path for path, _score in term_matches[:MAX_PREFILTER_FILES_PER_TERM]
        )
    return tuple(matched)


def _selected_paths(
    project_root: Path,
    term_capped: tuple[Path, ...],
    terms: tuple[str, ...],
    owner_path: str | None,
) -> tuple[Path, ...]:
    matched = ranked_capped_matches(project_root, term_capped)
    if owner_path is not None:
        owner_candidate = (project_root / owner_path).resolve()
        if owner_candidate.is_file() and owner_candidate.suffix == ".py":
            matched = (*matched, owner_candidate)
    return tuple(
        sorted(set(matched), key=lambda path: path_rank(project_root, path, terms))
    )


def _normalized_terms(query_terms: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(term.strip() for term in query_terms if term.strip()))


def _fd_available() -> bool:
    return shutil.which("fd") is not None or shutil.which("fdfind") is not None
