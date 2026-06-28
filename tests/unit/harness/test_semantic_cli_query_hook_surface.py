from pathlib import Path

from python_lang_project_harness._cli_args import ProtocolArgs


def test_query_from_hook_broad_selector_accepts_shared_surfaces() -> None:
    args = ProtocolArgs.parse(
        [
            "query",
            "--from-hook",
            "owner-local-projection",
            "--selector",
            "**/*.py",
            "--term",
            "HookDecision",
            "--surface",
            "owners,tests",
            "--view",
            "seeds",
            "--workspace",
            ".",
        ]
    )

    assert args is not None
    assert args.command == "error"
    assert args.error is not None
    assert "query --surface is Rust ASP search-owned" in args.error


def test_query_from_hook_accepts_workspace_selector_scope() -> None:
    args = ProtocolArgs.parse(
        [
            "query",
            "--from-hook",
            "owner-local-projection",
            "--workspace",
            ".",
            "--selector",
            "packages/example/src/example.py:1:20",
            "--source",
            "worktree",
            "--package",
            "packages/example",
            "--code",
        ]
    )

    assert args is not None
    assert args.command == "query"
    assert args.workspace is True
    assert args.project_root == Path(".")
    assert args.package_path == Path("packages/example")
    assert args.selector == "packages/example/src/example.py:1:20"
    assert args.source_version == "worktree"


def test_tree_sitter_query_accepts_workspace_selector_scope() -> None:
    args = ProtocolArgs.parse(
        [
            "query",
            "--treesitter-query",
            "(function_definition name: (identifier) @function.name)",
            "--workspace",
            ".",
            "--selector",
            "packages/example/src/example.py:1:20",
            "--package",
            "packages/example",
        ]
    )

    assert args is not None
    assert args.command == "query"
    assert args.workspace is True
    assert args.package_path == Path("packages/example")
    assert args.tree_sitter_query is not None
