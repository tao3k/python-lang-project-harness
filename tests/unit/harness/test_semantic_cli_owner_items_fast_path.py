"""Owner item fast-path tests for the Python semantic CLI."""

from __future__ import annotations

import io
import json
import time
from pathlib import Path

from semantic_search_fixture import write_search_fixture

from python_lang_project_harness import run_cli

OWNER_ITEMS_WARM_PATH_GATE_MS = 100.0


def test_cli_search_owner_items_query_uses_exact_owner_fast_path(
    tmp_path: Path,
    monkeypatch,
) -> None:
    write_search_fixture(tmp_path)
    json_stdout = io.StringIO()

    def fail_full_harness(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("owner-items should not run the full Python harness")

    from python_lang_project_harness import _runner

    monkeypatch.setattr(_runner, "run_python_project_harness", fail_full_harness)

    exit_code = run_cli(
        [
            "search",
            "owner",
            "src/pkg/service.py",
            "items",
            "--query",
            "fetch|build",
            "--json",
            "--workspace",
            str(tmp_path),
        ],
        stdout=json_stdout,
    )

    packet = json.loads(json_stdout.getvalue())
    assert exit_code == 0
    assert packet["runtimeCost"]["reason"] == "owner-items-exact-owner-prefilter"
    assert packet["runtimeCost"]["fields"] == {
        "ownerPath": "src/pkg/service.py",
        "paths": 1,
    }
    assert [item["name"] for item in packet["items"]] == ["fetch", "build"]


def test_cli_search_owner_items_query_stays_inside_warm_path_gate(
    tmp_path: Path,
) -> None:
    write_search_fixture(tmp_path)
    args = [
        "search",
        "owner",
        "src/pkg/service.py",
        "items",
        "--query",
        "fetch|build",
        "--json",
        "--workspace",
        str(tmp_path),
    ]

    warmup_stdout = io.StringIO()
    assert run_cli(args, stdout=warmup_stdout) == 0
    assert "owner-items-exact-owner-prefilter" in warmup_stdout.getvalue()

    timed_stdout = io.StringIO()
    started_at = time.perf_counter()
    exit_code = run_cli(args, stdout=timed_stdout)
    elapsed_ms = (time.perf_counter() - started_at) * 1000

    assert exit_code == 0
    assert "owner-items-exact-owner-prefilter" in timed_stdout.getvalue()
    assert elapsed_ms < OWNER_ITEMS_WARM_PATH_GATE_MS
