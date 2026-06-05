"""Projection-specific owner item query tests for the Python semantic CLI."""

from __future__ import annotations

import io
import json
from pathlib import Path

from python_lang_project_harness import run_cli


def test_cli_query_json_keeps_truncated_projection_rows_aligned_with_code(
    tmp_path: Path,
) -> None:
    package = tmp_path / "src" / "pkg"
    package.mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text(
        '\n[project]\nname = "demo-python"\nversion = "0.1.0"\nimport-names = ["pkg"]\n',
        encoding="utf-8",
    )
    (package / "__init__.py").write_text("", encoding="utf-8")
    body = ["class LargeShape:"]
    body.extend(f"    field_{index}: int" for index in range(35))
    (package / "model.py").write_text("\n".join(body), encoding="utf-8")
    stdout = io.StringIO()

    exit_code = run_cli(
        [
            "query",
            "src/pkg/model.py",
            "--term",
            "LargeShape",
            "--json",
            str(tmp_path),
        ],
        stdout=stdout,
    )

    packet = json.loads(stdout.getvalue())
    match = packet["matches"][0]
    projection = match["projection"]
    rows = projection["renderedRows"]
    assert exit_code == 0
    assert projection["nodesTruncated"] is True
    assert projection["nodeCount"] > projection["nodeLimit"]
    assert projection["omitted"]
    assert "\n".join(row["text"] for row in rows) == match["code"]


def test_cli_query_json_summarizes_dict_literal_returns(tmp_path: Path) -> None:
    package = tmp_path / "src" / "pkg"
    package.mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text(
        '\n[project]\nname = "demo-python"\nversion = "0.1.0"\nimport-names = ["pkg"]\n',
        encoding="utf-8",
    )
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "schema_fixture.py").write_text(
        "\n".join(
            [
                "def minimal_ast_patch_request() -> dict[str, str]:",
                "    return {",
                "        'schemaId': 'agent.semantic-protocols.semantic-ast-patch',",
                "        'schemaVersion': '1',",
                "        'protocolId': 'agent.semantic-protocols.ast-patch',",
                "        'protocolVersion': '1',",
                "        'languageId': 'python',",
                "        'providerId': 'py-harness',",
                "    }",
            ]
        ),
        encoding="utf-8",
    )
    stdout = io.StringIO()

    exit_code = run_cli(
        [
            "query",
            "src/pkg/schema_fixture.py",
            "--term",
            "minimal_ast_patch_request",
            "--json",
            str(tmp_path),
        ],
        stdout=stdout,
    )

    match = json.loads(stdout.getvalue())["matches"][0]
    assert exit_code == 0
    assert match["code"] == (
        "def minimal_ast_patch_request() -> dict[str, str]:\n"
        "  return dict[6] schemaId=agent.semantic-protocols.semantic-ast-patch "
        "schemaVersion=1 protocolId=agent.semantic-protocols.ast-patch "
        "protocolVersion=1 keys=languageId,providerId"
    )
    assert "return {'schemaId'" not in match["code"]
    assert "..." not in match["code"]
