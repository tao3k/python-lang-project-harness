import io
from pathlib import Path

from python_lang_project_harness import run_cli


def test_cli_query_names_only_without_owner_reports_fzf_route(
    tmp_path: Path,
) -> None:
    stdout = io.StringIO()
    stderr = io.StringIO()

    exit_code = run_cli(
        [
            "query",
            "--term",
            "run_install",
            "--names-only",
            "--workspace",
            str(tmp_path),
        ],
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 2
    assert stdout.getvalue() == ""
    assert stderr.getvalue() == (
        "query --names-only requires an owner selector; workspace term discovery is "
        "`search fzf '<term>' owner --view seeds --workspace <workspace-root>`\n"
    )
