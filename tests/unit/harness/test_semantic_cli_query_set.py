"""Semantic CLI query-set protocol tests."""

from __future__ import annotations

import io
import json
import shutil
from pathlib import Path

from semantic_search_fixture import (
    compact_graph_renderer_available,
    write_search_fixture,
)

from python_lang_project_harness import run_cli


def test_cli_search_text_query_set_and_flag_like_literal_query(
    tmp_path: Path,
) -> None:
    write_search_fixture(tmp_path)
    query_set_stdout = io.StringIO()
    query_set_json_stdout = io.StringIO()
    flag_like_stdout = io.StringIO()

    query_set_exit = run_cli(
        [
            "search",
            "fzf",
            "--query-set",
            "build",
            "--query-set",
            "Session",
            "owner",
            "tests",
            "--owner",
            "src/pkg/service.py",
            str(tmp_path),
        ],
        stdout=query_set_stdout,
    )
    query_set_json_exit = run_cli(
        [
            "search",
            "fzf",
            "--query-set",
            "build",
            "--query-set",
            "Session",
            "owner",
            "tests",
            "--owner",
            "src/pkg/service.py",
            "--json",
            str(tmp_path),
        ],
        stdout=query_set_json_stdout,
    )
    flag_like_exit = None
    if compact_graph_renderer_available():
        flag_like_exit = run_cli(
            ["search", "fzf", "--json", "--view", "seeds", str(tmp_path)],
            stdout=flag_like_stdout,
        )

    rendered = query_set_stdout.getvalue()
    assert query_set_exit == 0
    assert rendered.startswith('[search-fzf] q="build,Session" querySet=2')
    assert "selector=fuzzy-set" in rendered
    assert "scopeOwner=src/pkg/service.py" in rendered
    assert "|query build " in rendered
    assert "|query Session " in rendered
    assert "queryTerms=build" in rendered
    assert "queryTerms=Session" in rendered
    assert "|synthesis " in rendered
    assert "editFrontier=src/pkg/service.py" in rendered
    assert "windowSet=owner:src/pkg/service.py" in rendered
    assert "|seed owner:src/pkg/service.py" in rendered
    assert "|next owner:src/pkg/service.py,tests:src/pkg/service.py" in rendered
    for line in rendered.splitlines():
        if line.startswith("|seed "):
            assert ",owner:" not in line
            assert ",tests:" not in line
    assert "|edge O:src/pkg/service.py -test-> O:tests/test_service.py" in rendered

    packet = json.loads(query_set_json_stdout.getvalue())
    assert query_set_json_exit == 0
    assert packet["query"] == "build,Session"
    assert [term["value"] for term in packet["querySet"]] == ["build", "Session"]
    assert packet["queryComposition"]["mode"] == "query-set"
    assert packet["queryComposition"]["selector"] == "fuzzy-set"
    assert packet["queryComposition"]["merge"] == [
        "nodes",
        "edges",
        "owners",
        "hits",
        "typeSurfaces",
        "nextActions",
        "notes",
    ]
    assert packet["queryComposition"]["scope"]["ownerPath"] == "src/pkg/service.py"
    assert packet["header"]["fields"]["querySet"] == 2
    assert packet["header"]["fields"]["selector"] == "fuzzy-set"
    assert packet["header"]["fields"]["scopeOwner"] == "src/pkg/service.py"
    assert [query["value"] for query in packet["queryCoverage"]] == [
        "build",
        "Session",
    ]
    assert all(query["hitCount"] > 0 for query in packet["queryCoverage"])
    assert packet["ownerResolution"] == [
        {
            "target": "src/pkg/service.py",
            "status": "workspace-owner",
            "realOwner": True,
            "ownerPath": "src/pkg/service.py",
            "reason": "parser-visible owner selected by fzf search",
        }
    ]
    assert packet["searchSynthesis"]["seeds"] == [
        {"kind": "owner", "target": "src/pkg/service.py"}
    ]
    assert packet["searchSynthesis"]["windowSet"] == [
        {"kind": "owner", "target": "src/pkg/service.py"}
    ]
    assert packet["searchSynthesis"]["editFrontier"] == ["src/pkg/service.py"]
    assert "testFrontier" not in packet["searchSynthesis"]
    assert "runtimeCost" not in packet
    assert "|runtime " not in rendered

    if compact_graph_renderer_available():
        assert flag_like_exit == 0
        assert flag_like_stdout.getvalue().startswith("[search-fzf] q=--json")


def test_cli_search_text_prefilter_large_project_records_runtime_cost(
    tmp_path: Path,
) -> None:
    if shutil.which("rg") is None:
        return
    write_search_fixture(tmp_path)
    generated = tmp_path / "src" / "pkg" / "generated"
    generated.mkdir()
    for index in range(140):
        (generated / f"candidate_{index}.py").write_text(
            f'def large_need_{index}() -> str:\n    return "LargeNeedle-{index}"\n',
            encoding="utf-8",
        )

    stdout = io.StringIO()
    exit_code = run_cli(
        [
            "search",
            "fzf",
            "--query-set",
            "LargeNeedle",
            "--query-set",
            "large_need",
            "--query-set",
            "generated",
            "--owner",
            "src/pkg/service.py",
            "--json",
            str(tmp_path),
        ],
        stdout=stdout,
    )

    assert exit_code == 0
    packet = json.loads(stdout.getvalue())
    runtime_cost = packet["runtimeCost"]
    fields = runtime_cost["fields"]
    assert runtime_cost["sourceFilesParsed"] == fields["matchedFiles"]
    assert fields["candidateFiles"] > 128
    assert fields["minCandidateFiles"] == 128
    assert fields["mode"] == "text-query-prefilter"
    assert fields["queryTerms"] == 3
    assert fields["sourceSearchPasses"] == 1
    assert fields["fileListPasses"] == 1
    assert fields["candidateFileBasis"] == "all-python-files"
    assert fields["matchedFiles"] <= 17
    assert any(note["kind"] == "runtime-prefilter" for note in packet["notes"])


def test_cli_search_text_prefilter_skips_file_list_for_source_rich_terms(
    tmp_path: Path,
) -> None:
    if shutil.which("rg") is None:
        return
    write_search_fixture(tmp_path)
    generated = tmp_path / "src" / "pkg" / "generated"
    generated.mkdir()
    for index in range(140):
        (generated / f"source_rich_{index}.py").write_text(
            "\n".join(
                (
                    f"def LargeNeedle_{index}() -> str:",
                    f'    large_need = "generated-{index}"',
                    "    return large_need",
                    "",
                )
            ),
            encoding="utf-8",
        )

    stdout = io.StringIO()
    exit_code = run_cli(
        [
            "search",
            "fzf",
            "--query-set",
            "LargeNeedle",
            "--query-set",
            "large_need",
            "--query-set",
            "generated",
            "--json",
            str(tmp_path),
        ],
        stdout=stdout,
    )

    assert exit_code == 0
    packet = json.loads(stdout.getvalue())
    fields = packet["runtimeCost"]["fields"]
    assert fields["candidateFiles"] > 128
    assert fields["candidateFileBasis"] == "source-matched-files"
    assert fields["sourceSearchPasses"] == 1
    assert fields["fileListPasses"] == 0
    assert fields["prefilterTool"] == "rg"
    assert fields["matchedFiles"] <= 48
