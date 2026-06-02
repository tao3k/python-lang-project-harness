from python_lang_project_harness._cli_args import ProtocolArgs


def test_query_from_hook_broad_selector_accepts_shared_surfaces() -> None:
    args = ProtocolArgs.parse(
        [
            "query",
            "--from-hook",
            "direct-source-read",
            "--selector",
            "**/*.py",
            "--term",
            "HookDecision",
            "--surface",
            "owners,tests",
            "--view",
            "seeds",
            ".",
        ]
    )

    assert args is not None
    assert args.command == "search"
    assert args.view == "fzf"
    assert args.query == "HookDecision"
    assert args.query_set == ("HookDecision",)
    assert args.pipes == ("owner", "tests")
    assert args.render_mode == "seeds"
