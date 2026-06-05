"""Agent-facing guide and doctor rendering for the Python harness CLI."""

from __future__ import annotations

from pathlib import Path


def render_agent_guide(project_root: Path) -> str:
    root = str(project_root)
    return (
        "\n".join(
            (
                f"[py-harness-guide] project={root}",
                (
                    "|catalog reasoningProfiles=owner-query,query-deps,owner-tests,"
                    "finding-frontier,feature-cfg entries=owner-query,query-deps,"
                    "owner-tests routes=read-frontier"
                ),
                f"|cmd asp python search prime --view seeds {root}",
                f"|cmd asp python search owner <owner-path> --view seeds {root}",
                f"|cmd asp python query <owner-path> --term <symbol> --names-only {root}",
                f"|cmd asp python query <owner-path> --term <symbol> --code {root}",
                f"|cmd asp python query --catalog declarations --json {root}",
                (
                    f"|cmd asp python query --treesitter-query "
                    f"'<tree-sitter-query>' --json {root}"
                ),
                (
                    f"|cmd asp python search owner <owner-path> items "
                    f"--query <symbol|a|b> --code {root}"
                ),
                (
                    f"|cmd asp python search policy <rule-id-or-alias> "
                    f"owner tests --view seeds {root}"
                ),
                (
                    f"|cmd asp python query --from-hook direct-source-read "
                    f"--selector <selector> --term <term> --surface owners,tests "
                    f"--view seeds {root}"
                ),
                f"|cmd asp python search fzf <query> owner tests --view seeds {root}",
                f"|cmd asp python ast-patch dry-run --packet <semantic-ast-patch.json|-> {root}",
                f"|cmd asp python search deps <pkg[@ver][::api]> {root}",
                f"|pipe <candidate-lines> | asp python search ingest --view seeds {root}",
                f"|cmd asp python check --changed {root}",
                "|rule agent hook install/runtime is owned by asp",
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
