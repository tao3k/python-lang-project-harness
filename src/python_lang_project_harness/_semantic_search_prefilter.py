"""Fast candidate-file pruning for Python semantic fzf search."""

from __future__ import annotations

import shutil
import time
from pathlib import Path
from typing import TYPE_CHECKING

from ._semantic_search_prefilter_file_scan import (
    python_file_path_matches_by_term,
)
from ._semantic_search_prefilter_path import path_only_term_capped_matches
from ._semantic_search_prefilter_rank import (
    MAX_PREFILTER_FILES_PER_TERM,
    path_key_rank,
    ranked_capped_matches,
    ranked_term_matches,
)
from ._semantic_search_prefilter_result import (
    MIN_PREFILTER_FILES,
    PythonSearchPrefilterResult,
)
from ._semantic_search_prefilter_tools import (
    source_match_scores_by_term,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


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
    path_match_scan = python_file_path_matches_by_term(
        project_root,
        terms,
        rg=rg,
    )
    path_only_term_capped = path_only_term_capped_matches(
        project_root,
        terms,
        path_match_scan,
    )
    if path_only_term_capped is not None:
        selected = _selected_paths(
            project_root,
            path_only_term_capped,
            terms,
            owner_path,
        )
        elapsed_ms = round((time.perf_counter() - started) * 1000)
        return PythonSearchPrefilterResult(
            paths=selected,
            total_files=path_match_scan.total_files,
            term_capped_files=len(set(path_only_term_capped)),
            matched_files=len(selected),
            elapsed_ms=elapsed_ms,
            tool=path_match_scan.tool,
            reason="rg/fd path prefilter selected parser input files for fzf query",
            query_terms=len(terms),
            source_search_passes=0,
            file_list_passes=1,
            candidate_file_basis="path-matched-files",
        )

    source_scores_by_term = source_match_scores_by_term(project_root, rg, terms)
    source_matched_files = _source_matched_files(source_scores_by_term)
    source_only_term_capped = _source_only_term_capped_matches(
        project_root,
        terms,
        source_scores_by_term,
        source_matched_files,
    )
    if source_only_term_capped is not None:
        selected = _selected_paths(
            project_root,
            source_only_term_capped,
            terms,
            owner_path,
        )
        elapsed_ms = round((time.perf_counter() - started) * 1000)
        return PythonSearchPrefilterResult(
            paths=selected,
            total_files=len(source_matched_files),
            term_capped_files=len(set(source_only_term_capped)),
            matched_files=len(selected),
            elapsed_ms=elapsed_ms,
            tool="rg",
            reason="rg source prefilter selected parser input files for fzf query",
            query_terms=len(terms),
            source_search_passes=1 if terms else 0,
            file_list_passes=0,
            candidate_file_basis="source-matched-files",
        )

    if path_match_scan.total_files <= MIN_PREFILTER_FILES:
        return None
    term_capped = _term_capped_matches(
        project_root,
        terms,
        path_match_scan.matches_by_term,
        source_scores_by_term,
    )
    selected = _selected_paths(project_root, term_capped, terms, owner_path)
    elapsed_ms = round((time.perf_counter() - started) * 1000)
    return PythonSearchPrefilterResult(
        paths=selected,
        total_files=path_match_scan.total_files,
        term_capped_files=len(set(term_capped)),
        matched_files=len(selected),
        elapsed_ms=elapsed_ms,
        tool=path_match_scan.tool,
        reason="rg/fd prefilter selected parser input files for fzf query",
        query_terms=len(terms),
        source_search_passes=1 if terms else 0,
        file_list_passes=1,
        candidate_file_basis="all-python-files",
    )


def _source_only_term_capped_matches(
    project_root: Path,
    terms: tuple[str, ...],
    source_scores_by_term: dict[str, dict[str, int]],
    source_matched_files: frozenset[str],
) -> tuple[str, ...] | None:
    if not _source_only_prefilter_is_sufficient(
        terms,
        source_scores_by_term,
        source_matched_files,
    ):
        return None
    matched: list[str] = []
    for term in terms:
        term_matches = ranked_term_matches(
            project_root,
            term,
            set(),
            source_scores_by_term.get(term, {}),
        )
        matched.extend(
            path for path, _score in term_matches[:MAX_PREFILTER_FILES_PER_TERM]
        )
    return tuple(matched)


def _term_capped_matches(
    project_root: Path,
    terms: tuple[str, ...],
    path_matches_by_term: dict[str, set[str]],
    source_scores_by_term: dict[str, dict[str, int]],
) -> tuple[str, ...]:
    matched: list[str] = []
    for term in terms:
        term_matches = ranked_term_matches(
            project_root,
            term,
            path_matches_by_term.get(term, set()),
            source_scores_by_term.get(term, {}),
        )
        matched.extend(
            path for path, _score in term_matches[:MAX_PREFILTER_FILES_PER_TERM]
        )
    return tuple(matched)


def _selected_paths(
    project_root: Path,
    term_capped: tuple[str, ...],
    terms: tuple[str, ...],
    owner_path: str | None,
) -> tuple[Path, ...]:
    matched = ranked_capped_matches(project_root, term_capped)
    if owner_path is not None:
        owner_candidate = (project_root / owner_path).resolve()
        if owner_candidate.is_file() and owner_candidate.suffix == ".py":
            matched = (*matched, owner_path)
    return tuple(
        project_root / path
        for path in sorted(set(matched), key=lambda path: path_key_rank(path, terms))
    )


def _normalized_terms(query_terms: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(term.strip() for term in query_terms if term.strip()))


def _source_only_prefilter_is_sufficient(
    terms: tuple[str, ...],
    source_scores_by_term: dict[str, dict[str, int]],
    source_matched_files: frozenset[str],
) -> bool:
    return (
        bool(terms)
        and len(source_matched_files) > MIN_PREFILTER_FILES
        and all(
            len(source_scores_by_term.get(term, {})) >= MAX_PREFILTER_FILES_PER_TERM
            for term in terms
        )
    )


def _source_matched_files(
    source_scores_by_term: dict[str, dict[str, int]],
) -> frozenset[str]:
    return frozenset(
        path
        for source_scores in source_scores_by_term.values()
        for path in source_scores
    )
