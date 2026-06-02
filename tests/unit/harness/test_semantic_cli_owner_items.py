"""Owner item query tests for the Python semantic CLI."""

from __future__ import annotations

import io
import json
from pathlib import Path

from semantic_search_fixture import write_search_fixture

from python_lang_project_harness import run_cli


def test_cli_search_owner_items_query_returns_compact_code(tmp_path: Path) -> None:
    write_search_fixture(tmp_path)
    stdout = io.StringIO()
    json_stdout = io.StringIO()

    exit_code = run_cli(
        [
            "search",
            "owner",
            "src/pkg/service.py",
            "items",
            "--query",
            "fetch|build",
            str(tmp_path),
        ],
        stdout=stdout,
    )
    json_exit_code = run_cli(
        [
            "search",
            "owner",
            "src/pkg/service.py",
            "items",
            "--query",
            "fetch|build",
            "--json",
            str(tmp_path),
        ],
        stdout=json_stdout,
    )

    rendered = stdout.getvalue()
    assert exit_code == 0
    assert rendered.startswith("[search-owner] q=src/pkg/service.py owner=1")
    assert "item=2 itemQuery=fetch|build itemStatus=hit itemMatch=exact" in rendered
    assert "|query itemQuery=fetch|build status=hit match=exact item=2" in rendered
    assert "|item fetch kind=function" in rendered
    assert "public=false" not in rendered
    assert "doc=false" not in rendered
    assert "read=src/pkg/service.py:" in rendered
    assert "|item build kind=function" in rendered
    assert 'text="def fetch() -> Response:\\n  return Response()"' in rendered
    assert 'text="def build(value: str) -> str:\\n  return value.strip()"' in rendered
    assert "    return value.strip()" not in rendered

    packet = json.loads(json_stdout.getvalue())
    assert json_exit_code == 0
    assert packet["items"][0]["name"] == "fetch"
    assert packet["items"][0]["fields"]["code"] == (
        "def fetch() -> Response:\n  return Response()"
    )
    assert packet["items"][1]["name"] == "build"


def test_cli_search_owner_items_code_flag_returns_pure_compact_code(
    tmp_path: Path,
) -> None:
    write_search_fixture(tmp_path)
    stdout = io.StringIO()

    exit_code = run_cli(
        [
            "search",
            "owner",
            "src/pkg/service.py",
            "items",
            "--query",
            "build",
            "--code",
            str(tmp_path),
        ],
        stdout=stdout,
    )

    rendered = stdout.getvalue()
    assert exit_code == 0
    assert rendered == "def build(value: str) -> str:\n  return value.strip()\n"
    assert "[search-owner]" not in rendered
    assert "|code" not in rendered


def test_cli_search_owner_items_code_flag_rejects_json(tmp_path: Path) -> None:
    write_search_fixture(tmp_path)
    stdout = io.StringIO()
    stderr = io.StringIO()

    exit_code = run_cli(
        [
            "search",
            "owner",
            "src/pkg/service.py",
            "items",
            "--query",
            "build",
            "--code",
            "--json",
            str(tmp_path),
        ],
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 2
    assert "--code cannot be combined with --json" in stderr.getvalue()


def test_cli_search_owner_items_query_miss_returns_owner_top_items(
    tmp_path: Path,
) -> None:
    write_search_fixture(tmp_path)
    stdout = io.StringIO()

    exit_code = run_cli(
        [
            "search",
            "owner",
            "src/pkg/service.py",
            "items",
            "--query",
            "missingSymbol",
            str(tmp_path),
        ],
        stdout=stdout,
    )

    rendered = stdout.getvalue()
    assert exit_code == 0
    assert "itemStatus=miss" in rendered
    assert "fallback=owner-top-items" in rendered
    assert "|query itemQuery=missingSymbol status=miss" in rendered
    assert "|item SessionClient kind=class" in rendered
    assert "read=src/pkg/service.py:" in rendered


def test_cli_search_owner_items_query_matches_function_body_text(
    tmp_path: Path,
) -> None:
    write_search_fixture(tmp_path)
    stdout = io.StringIO()

    exit_code = run_cli(
        [
            "search",
            "owner",
            "src/pkg/service.py",
            "items",
            "--query",
            "value.strip",
            str(tmp_path),
        ],
        stdout=stdout,
    )

    rendered = stdout.getvalue()
    assert exit_code == 0
    assert (
        "itemQuery=value.strip itemStatus=hit itemMatch=fallback-contains" in rendered
    )
    assert "|item build kind=function" in rendered
    assert "read=src/pkg/service.py:" in rendered
    assert "return value.strip()" in rendered


def test_cli_query_json_emits_projection_nodes_and_expand_actions(
    tmp_path: Path,
) -> None:
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
    projection = packet["matches"][0]["projection"]
    assert exit_code == 0
    assert any(node["read"] != projection["exactRead"] for node in projection["nodes"])
    assert any(
        node.get("parentId") not in {None, "decide"} for node in projection["nodes"]
    )
    assert any(
        action.get("target") != "decide"
        and action.get("read") != projection["exactRead"]
        for action in projection["expandActions"]
    )
    for action in projection["expandActions"]:
        if action.get("kind") != "exact-read":
            continue
        argv = action["argv"]
        selector_index = argv.index("--selector")
        assert argv[selector_index + 1] == action["read"]


def test_cli_query_direct_source_read_selector_strips_line_range(
    tmp_path: Path,
) -> None:
    package = tmp_path / "src" / "pkg"
    package.mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text(
        '\n[project]\nname = "demo-python"\nversion = "0.1.0"\nimport-names = ["pkg"]\n',
        encoding="utf-8",
    )
    (package / "__init__.py").write_text("", encoding="utf-8")
    source = "\n".join(
        [
            "def first() -> int:",
            "    return 1",
            "def second() -> int:",
            "    return 2",
            "def third() -> int:",
            "    return 3",
            "def fourth() -> int:",
            "    return 4",
            "def fifth() -> int:",
            "    return 5",
            "def target() -> int:",
            "    return 6",
        ]
    )
    target_start = source.splitlines().index("def target() -> int:") + 1
    selector = f"src/pkg/service.py:{target_start}:{target_start + 1}"
    (package / "service.py").write_text(source, encoding="utf-8")
    stdout = io.StringIO()

    exit_code = run_cli(
        [
            "query",
            "--from-hook",
            "direct-source-read",
            "--selector",
            selector,
            "--json",
            str(tmp_path),
        ],
        stdout=stdout,
    )

    packet = json.loads(stdout.getvalue())
    assert exit_code == 0
    assert packet["ownerPath"] == "src/pkg/service.py"
    assert [match["name"] for match in packet["matches"]] == ["target"]
    assert packet["matches"][0]["read"] == selector
