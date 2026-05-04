"""Verification profile index built from parser project facts."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from .._render import _render_display_path
from .._rule_packs import resolve_project_harness_config
from .._runner import run_python_project_harness
from .facts import (
    entry_point_owner_paths,
    is_test_path,
    matched_dependency_signals,
    node_evidence,
    node_responsibilities,
    project_metadata_owner_path,
    require_dependency_name,
    verification_project_root,
    verification_reasoning_tree_facts,
)
from .model import (
    PythonOwnerResponsibility,
    PythonVerificationEvidence,
    PythonVerificationPolicy,
    PythonVerificationProfileCandidate,
    PythonVerificationProfileHint,
    PythonVerificationProfileIndex,
    PythonVerificationTaskKind,
)

if TYPE_CHECKING:
    from .._model import PythonHarnessConfig, PythonHarnessReport


def build_python_verification_profile_index(
    project_root: str | Path,
) -> PythonVerificationProfileIndex:
    """Build parser-suggested verification profile candidates for one project."""

    return build_python_verification_profile_index_with_config(project_root, None)


def build_python_verification_profile_index_with_config(
    project_root: str | Path,
    config: PythonHarnessConfig | None,
) -> PythonVerificationProfileIndex:
    """Build profile candidates with an explicit harness config."""

    root = Path(project_root)
    selected_config = resolve_project_harness_config(root, config, rule_packs=None)
    report = run_python_project_harness(root, config=selected_config)
    return build_python_verification_profile_index_report(report, selected_config)


def build_python_verification_profile_index_report(
    report: PythonHarnessReport,
    config: PythonHarnessConfig,
) -> PythonVerificationProfileIndex:
    """Build profile candidates from an already-built harness report."""

    project_root = verification_project_root(report)
    policy = config.verification_policy
    facts = verification_reasoning_tree_facts(report)
    candidates: list[PythonVerificationProfileCandidate] = []
    candidate_index_by_path: dict[str, int] = {}
    aggregate_public_namespaces = frozenset(
        branch.namespace for branch in facts.branches if branch.has_public_surface
    )
    for node in facts.nodes:
        path = _render_display_path(node.path, project_root=project_root)
        if is_test_path(path):
            continue
        responsibilities = _responsibilities_for_node(
            node_responsibilities(node),
            namespace=node.namespace,
            aggregate_public_namespaces=aggregate_public_namespaces,
        )
        if responsibilities:
            _append_candidate(
                candidates,
                candidate_index_by_path,
                owner_path=path,
                owner_namespace=node.namespace,
                responsibilities=responsibilities,
                evidence=node_evidence(node),
                policy=policy,
            )
    metadata = facts.project_metadata
    if metadata is not None:
        metadata_owner_path = project_metadata_owner_path(
            facts,
            project_root=project_root,
        )
        for path, namespace in entry_point_owner_paths(
            facts,
            project_root=project_root,
        ):
            _append_candidate(
                candidates,
                candidate_index_by_path,
                owner_path=path,
                owner_namespace=namespace,
                responsibilities=(PythonOwnerResponsibility.CLI,),
                evidence=(PythonVerificationEvidence("entry-point", "true"),),
                policy=policy,
            )
        if metadata_owner_path is not None and (
            metadata.pytest_options.enables_python_project_harness
            or any(entry.group == "pytest11" for entry in metadata.entry_points)
        ):
            _append_candidate(
                candidates,
                candidate_index_by_path,
                owner_path=metadata_owner_path,
                owner_namespace=(),
                responsibilities=(PythonOwnerResponsibility.PYTEST_GATE,),
                evidence=(PythonVerificationEvidence("pytest-gate", "true"),),
                policy=policy,
            )
        for dependency, signal in matched_dependency_signals(
            metadata.dependencies,
            policy.dependency_signals,
        ):
            if metadata_owner_path is None:
                continue
            _append_candidate(
                candidates,
                candidate_index_by_path,
                owner_path=metadata_owner_path,
                owner_namespace=(),
                responsibilities=signal.responsibilities,
                evidence=(
                    PythonVerificationEvidence(
                        "dependency",
                        require_dependency_name(dependency),
                    ),
                ),
                task_kinds=signal.task_kinds,
                policy=policy,
            )
    return PythonVerificationProfileIndex(
        project_root=project_root,
        candidates=tuple(sorted(candidates, key=lambda item: item.owner_path)),
    )


def _responsibilities_for_node(
    responsibilities: tuple[PythonOwnerResponsibility, ...],
    *,
    namespace: tuple[str, ...],
    aggregate_public_namespaces: frozenset[tuple[str, ...]],
) -> tuple[PythonOwnerResponsibility, ...]:
    if not responsibilities:
        return ()
    if not any(
        responsibility == PythonOwnerResponsibility.PUBLIC_API
        for responsibility in responsibilities
    ):
        return responsibilities
    if not _is_covered_by_public_branch(
        namespace,
        aggregate_public_namespaces=aggregate_public_namespaces,
    ):
        return responsibilities
    return tuple(
        responsibility
        for responsibility in responsibilities
        if responsibility != PythonOwnerResponsibility.PUBLIC_API
    )


def _is_covered_by_public_branch(
    namespace: tuple[str, ...],
    *,
    aggregate_public_namespaces: frozenset[tuple[str, ...]],
) -> bool:
    return any(
        namespace != branch_namespace
        and len(namespace) > len(branch_namespace)
        and namespace[: len(branch_namespace)] == branch_namespace
        for branch_namespace in aggregate_public_namespaces
    )


def _append_candidate(
    candidates: list[PythonVerificationProfileCandidate],
    candidate_index_by_path: dict[str, int],
    *,
    owner_path: str,
    owner_namespace: tuple[str, ...],
    responsibilities: tuple[PythonOwnerResponsibility, ...],
    evidence: tuple[PythonVerificationEvidence, ...],
    policy: PythonVerificationPolicy,
    task_kinds: tuple[PythonVerificationTaskKind, ...] = (),
) -> None:
    existing_index = candidate_index_by_path.get(owner_path)
    effective_task_kinds = task_kinds or policy.task_kinds_for_responsibilities(
        responsibilities
    )
    if existing_index is not None:
        existing = candidates[existing_index]
        combined_responsibilities = _merge_tuple(
            existing.responsibilities,
            responsibilities,
        )
        combined_task_kinds = _merge_tuple(existing.task_kinds, effective_task_kinds)
        combined_evidence = _merge_tuple(existing.evidence, evidence)
        candidates[existing_index] = PythonVerificationProfileCandidate(
            owner_path=owner_path,
            owner_namespace=existing.owner_namespace or owner_namespace,
            responsibilities=combined_responsibilities,
            state=_candidate_state(owner_path, combined_responsibilities, policy),
            configured_responsibilities=_configured_responsibilities(
                owner_path,
                policy,
            ),
            evidence=combined_evidence,
            task_kinds=combined_task_kinds,
        )
        return
    candidate_index_by_path[owner_path] = len(candidates)
    candidates.append(
        PythonVerificationProfileCandidate(
            owner_path=owner_path,
            owner_namespace=owner_namespace,
            responsibilities=responsibilities,
            state=_candidate_state(owner_path, responsibilities, policy),
            configured_responsibilities=_configured_responsibilities(
                owner_path,
                policy,
            ),
            evidence=evidence,
            task_kinds=effective_task_kinds,
        )
    )


def _candidate_state(
    owner_path: str,
    responsibilities: tuple[PythonOwnerResponsibility, ...],
    policy: PythonVerificationPolicy,
) -> str:
    hint = _matching_hint(owner_path, policy.profile_hints)
    if hint is None:
        return "missing_profile"
    if set(responsibilities).issubset(set(hint.responsibilities)):
        return "configured"
    return "profile_drift"


def _configured_responsibilities(
    owner_path: str,
    policy: PythonVerificationPolicy,
) -> tuple[PythonOwnerResponsibility, ...]:
    hint = _matching_hint(owner_path, policy.profile_hints)
    if hint is None:
        return ()
    return hint.responsibilities


def _merge_tuple[T](left: tuple[T, ...], right: tuple[T, ...]) -> tuple[T, ...]:
    merged = list(left)
    for item in right:
        if item in merged:
            continue
        merged.append(item)
    return tuple(merged)


def _matching_hint(
    owner_path: str,
    hints: tuple[PythonVerificationProfileHint, ...],
) -> PythonVerificationProfileHint | None:
    return next((hint for hint in hints if hint.owner_path == owner_path), None)
