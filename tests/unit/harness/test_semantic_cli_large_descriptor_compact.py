from __future__ import annotations

import io
from pathlib import Path

from python_lang_project_harness._cli import run_cli


def test_cli_query_compacts_large_descriptor_return_lists(tmp_path: Path) -> None:
    package = tmp_path / "src" / "pkg"
    package.mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text(
        """
[project]
name = "demo-python"
version = "0.1.0"
import-names = ["pkg"]
""".strip(),
        encoding="utf-8",
    )
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "catalog.py").write_text(
        "\n".join(
            [
                "from typing import Any",
                "",
                "def python_search_view_descriptors() -> list[dict[str, Any]]:",
                "    return [",
                "        _view('workspace', capabilities=[_semantic('workspace-router')]),",
                "        _view('prime', capabilities=[_semantic('package-prime-map')]),",
                "        _view('owner', requires_query=True, accepted_pipes=['items']),",
                "        _view('dependency', requires_query=True),",
                "        _view('deps', requires_query=True),",
                "        _view('api', requires_query=True),",
                "        _view('policy', requires_query=True),",
                "    ]",
            ]
        ),
        encoding="utf-8",
    )

    stdout = io.StringIO()
    exit_code = run_cli(
        [
            "query",
            "src/pkg/catalog.py",
            "--term",
            "python_search_view_descriptors",
            str(tmp_path),
        ],
        stdout=stdout,
    )

    output = stdout.getvalue()
    assert exit_code == 0
    assert "return list[7] items=_view:workspace,_view:prime,_view:owner" in output
    assert "capabilities=[" not in output
    assert "truncated=true" not in output
