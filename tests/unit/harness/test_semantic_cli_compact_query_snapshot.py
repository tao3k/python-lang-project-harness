"""Compact query snapshot tests for the Python semantic CLI."""

from __future__ import annotations

import io
import json
from pathlib import Path

from python_lang_project_harness import run_cli


def _compact_query_snapshot(packet: dict) -> dict:
    return {
        "matches": [
            {
                "name": match["name"],
                "kind": match["kind"],
                "read": match["read"],
                "code": match.get("code"),
                "projection": match.get("projection"),
            }
            for match in packet["matches"]
        ]
    }


def _read_json_fixture(relative_path: str) -> dict:
    fixture_path = Path(__file__).resolve().parents[2] / "fixtures" / relative_path
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def test_cli_query_compact_packet_matches_parser_snapshot(tmp_path: Path) -> None:
    package = tmp_path / "src" / "pkg"
    package.mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text(
        '\n[project]\nname = "demo-python"\nversion = "0.1.0"\nimport-names = ["pkg"]\n',
        encoding="utf-8",
    )
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "service.py").write_text(
        "\n".join(
            [
                "def decide(value: int) -> int:",
                "    if value > 0:",
                "        return value",
                "    return 0",
            ]
        ),
        encoding="utf-8",
    )
    stdout = io.StringIO()

    exit_code = run_cli(
        [
            "query",
            "src/pkg/service.py",
            "--term",
            "decide",
            "--json",
            str(tmp_path),
        ],
        stdout=stdout,
    )

    packet = json.loads(stdout.getvalue())
    assert exit_code == 0
    assert _compact_query_snapshot(packet) == _read_json_fixture(
        "compact-query/python-decide.json"
    )


def test_cli_query_flow_compact_packet_matches_parser_snapshot(
    tmp_path: Path,
) -> None:
    package = tmp_path / "src" / "pkg"
    package.mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text(
        '\n[project]\nname = "demo-python"\nversion = "0.1.0"\nimport-names = ["pkg"]\n',
        encoding="utf-8",
    )
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "flow.py").write_text(
        "\n".join(
            [
                "async def collect(values: list[str], normalize) -> list[str]:",
                "    results: list[str] = []",
                "    for value in values:",
                "        if not value:",
                "            continue",
                "        results.append(await normalize(value))",
                "    return results",
            ]
        ),
        encoding="utf-8",
    )
    stdout = io.StringIO()

    exit_code = run_cli(
        [
            "query",
            "src/pkg/flow.py",
            "--term",
            "collect",
            "--json",
            str(tmp_path),
        ],
        stdout=stdout,
    )

    packet = json.loads(stdout.getvalue())
    assert exit_code == 0
    assert _compact_query_snapshot(packet) == _read_json_fixture(
        "compact-query/python-flow.json"
    )
