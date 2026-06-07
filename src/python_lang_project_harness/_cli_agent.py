"""Agent-facing guide and doctor rendering for the Python harness CLI."""

from __future__ import annotations

from pathlib import Path


def render_agent_guide(project_root: Path) -> str:
    project = str(project_root)
    root = "."
    return (
        "\n".join(
            (
                f"[py-harness-guide] project={project}",
                (
                    "|catalog reasoningProfiles=owner-query,query-deps,owner-tests,"
                    "finding-frontier,feature-cfg entries=owner-query,query-deps,"
                    "owner-tests routes=read-frontier,syntax-locate,syntax-code,"
                    "query-code"
                ),
                "|flow prime->owner|syntax-locate|query-code|deps|tests "
                "pipe=fzf:tests ingest=stdin",
                (
                    f"|route syntax-locate selectors=S:tree-sitter-query,R:range "
                    f"returns=locator,capture,frontier code=false cmd=asp python "
                    f"query --treesitter-query "
                    f"'(function_definition name: (identifier) @function.name)' "
                    f"--selector <path[:line|:start:end]> {root}"
                ),
                (
                    f"|route syntax-code selectors=S:tree-sitter-query,R:exact-selector "
                    f"returns=code code=pure cmd=asp python query --treesitter-query "
                    f"'(function_definition name: (identifier) @function.name)' "
                    f"--selector <path[:line|:start:end]> --code {root}"
                ),
                (
                    f"|route read-plan selectors=R:selector,T:term "
                    f"returns=owners,tests,window-set code=false cmd=asp python "
                    f"query --from-hook direct-source-read --selector <selector> "
                    f"--term <term> --surface owners,tests --view seeds {root}"
                ),
                (
                    f"|route query-code selectors=O:owner,Q:symbol returns=code "
                    f"code=pure cmd=asp python query <owner-path> --term <symbol> "
                    f"--code {root}"
                ),
                f"|cmd prime=asp python search prime --view seeds {root}",
                f"|cmd owner=asp python search owner <owner-path> --view seeds {root}",
                (
                    f"|cmd reasoning-owner-tests=asp python search reasoning "
                    f"owner-tests --owner <owner-path> --view seeds {root}"
                ),
                (
                    f"|cmd reasoning-owner-query=asp python search reasoning "
                    f"owner-query --owner <owner-path> --query <symbol> "
                    f"--view seeds {root}"
                ),
                (
                    f"|cmd reasoning-query-deps=asp python search reasoning "
                    f"query-deps --query <symbol> --dependency <pkg> "
                    f"--view seeds {root}"
                ),
                f"|cmd names=asp python query <owner-path> --term <symbol> --names-only {root}",
                f"|cmd query-code=asp python query <owner-path> --term <symbol> --code {root}",
                f"|cmd catalog-json=asp python query --catalog declarations --json {root}",
                (
                    f"|cmd syntax-locate=asp python query --treesitter-query "
                    f"'(function_definition name: (identifier) @function.name)' "
                    f"--selector <path[:line|:start:end]> {root}"
                ),
                (
                    f"|cmd syntax-code=asp python query --treesitter-query "
                    f"'(function_definition name: (identifier) @function.name)' "
                    f"--selector <path[:line|:start:end]> --code {root}"
                ),
                (
                    f"|cmd owner-items-code=asp python search owner <owner-path> items "
                    f"--query <symbol|a|b> --code {root}"
                ),
                (
                    f"|cmd policy=asp python search policy <rule-id-or-alias> "
                    f"owner tests --view seeds {root}"
                ),
                (
                    f"|cmd read-plan=asp python query --from-hook direct-source-read "
                    f"--selector <selector> --term <term> --surface owners,tests "
                    f"--view seeds {root}"
                ),
                f"|cmd fzf=asp python search fzf <query> owner tests --view seeds {root}",
                f"|cmd ast-patch=asp python ast-patch dry-run --packet <semantic-ast-patch.json|-> {root}",
                f"|cmd deps=asp python search deps <pkg[@ver][::api]> {root}",
                f"|pipe <candidate-lines> | asp python search ingest --view seeds {root}",
                f"|cmd check=asp python check --changed {root}",
                "|rule agent hook install/runtime is owned by asp",
                "|rule run guide commands from project root; trailing . is the project root",
                (
                    "|rule syntax query ABI is compiled by asp; provider projects "
                    "native parser facts into tree-sitter-compatible captures"
                ),
                (
                    "|rule syntax predicates supported=#eq?,#any-eq?,#any-of?,"
                    "#match?,#any-match?,#not-eq?,#not-match? "
                    "unsupported=none unsupportedReported=true"
                ),
                (
                    "|rule query --code is pure code; search/read-plan returns "
                    "locators/frontier, not inline code"
                ),
                (
                    "|rule use the asp python facade; run one command at a time; "
                    "no raw Python source reads"
                ),
                "|subagent give one |cmd or |pipe line; require evidence/missing/next/risk",
            )
        )
        + "\n"
    )


def render_agent_doctor(project_root: Path) -> str:
    from . import _semantic_language_ids as ids
    from ._semantic_language import python_semantic_language_registration

    registration = python_semantic_language_registration()
    return (
        "\n".join(
            (
                "[agent-doctor] "
                f"status=ok protocol={ids.SEMANTIC_LANGUAGE_PROTOCOL_ID} "
                f"registry=semantic-language-registry.v{ids.SEMANTIC_LANGUAGE_REGISTRY_VERSION}",
                f"|project {project_root}",
                (
                    f"|language id={ids.PYTHON_LANGUAGE_ID} provider={ids.PYTHON_PROVIDER_ID} "
                    f"binary={ids.PYTHON_BINARY}"
                ),
                f"|namespace {ids.PYTHON_PROVIDER_NAMESPACE}",
                f"|method {','.join(registration['methods'])}",
                "|schema semantic-search-packet.v1",
            )
        )
        + "\n"
    )


def render_agent_doctor_json(project_root: Path) -> str:
    import json

    from ._semantic_language import semantic_language_registry_document

    return (
        json.dumps(
            semantic_language_registry_document(str(project_root)),
            separators=(",", ":"),
        )
        + "\n"
    )
