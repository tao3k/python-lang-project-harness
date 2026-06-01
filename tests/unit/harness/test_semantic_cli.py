"""Semantic CLI protocol tests for the Python harness provider."""

from __future__ import annotations

import io
import json
from pathlib import Path

from semantic_search_fixture import write_search_fixture

from python_lang_project_harness import python_semantic_language_registration, run_cli


def test_cli_agent_doctor_json_advertises_semantic_language_provider(
    tmp_path: Path,
) -> None:
    stdout = io.StringIO()

    exit_code = run_cli(["agent", "doctor", "--json", str(tmp_path)], stdout=stdout)
    payload = json.loads(stdout.getvalue())

    assert exit_code == 0
    registration = payload["languages"][0]
    assert registration["languageId"] == "python"
    assert registration["providerId"] == "py-harness"
    assert registration["binary"] == "py-harness"
    assert registration["namespace"] == (
        "agent.semantic-protocols.languages.python.py-harness"
    )
    assert "search/workspace" in registration["methods"]
    assert "search/callsite" in registration["methods"]
    assert "search/public-external-types" in registration["methods"]
    assert "search/text" in registration["methods"]
    assert "agent/doctor" in registration["methods"]
    assert "agent/guide" in registration["methods"]
    assert "agent/install" not in registration["methods"]
    assert "agent/hook" not in registration["methods"]
    assert any(
        descriptor["method"] == "search/text"
        and descriptor["acceptedPipes"] == ["owner", "tests"]
        and descriptor["supportsQuerySet"] is True
        and descriptor["acceptedQuerySetSelectors"] == ["exact-set"]
        and descriptor["querySetScopes"] == ["project", "owner"]
        for descriptor in registration["methodDescriptors"]
    )
    assert not any(
        descriptor["method"] in {"agent/install", "agent/hook"}
        for descriptor in registration["methodDescriptors"]
    )
    assert any(
        descriptor["method"] == "agent/guide"
        and descriptor["command"] == "agent"
        and descriptor["supportsCompact"] is True
        and descriptor["supportsJson"] is False
        for descriptor in registration["methodDescriptors"]
    )


def test_cli_agent_guide_prints_provider_owned_searchflow(tmp_path: Path) -> None:
    stdout = io.StringIO()

    exit_code = run_cli(["agent", "guide", str(tmp_path)], stdout=stdout)

    rendered = stdout.getvalue()
    assert exit_code == 0
    assert rendered.startswith(f"[py-harness-guide] project={tmp_path}")
    assert f"|cmd py-harness search prime --view seeds {tmp_path}" in rendered
    assert (
        f"|cmd py-harness search owner <owner-path> --view seeds {tmp_path}" in rendered
    )
    assert "|rule use installed py-harness binary" in rendered


def test_python_capability_schema_covers_registry_descriptors() -> None:
    schema_path = (
        Path(__file__).resolve().parents[3]
        / "schemas"
        / "python-semantic-capabilities.v1.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    capability_names = set(
        schema["$defs"]["capabilityDescriptor"]["properties"]["name"]["enum"]
    )
    ingest_names = set(
        schema["$defs"]["ingestSurfaceDescriptor"]["properties"]["name"]["enum"]
    )

    for descriptor in python_semantic_language_registration()["methodDescriptors"]:
        for capability in descriptor.get("capabilities", []):
            assert capability["name"] in capability_names
        for ingest_surface in descriptor.get("ingestRequiredFor", []):
            assert ingest_surface["name"] in ingest_names


def test_cli_search_workspace_prime_and_text_pipe(tmp_path: Path) -> None:
    write_search_fixture(tmp_path)

    workspace_stdout = io.StringIO()
    prime_stdout = io.StringIO()
    text_stdout = io.StringIO()

    assert run_cli(["search", "workspace", str(tmp_path)], stdout=workspace_stdout) == 0
    assert run_cli(["search", "prime", str(tmp_path)], stdout=prime_stdout) == 0
    assert (
        run_cli(
            ["search", "text", "build", "owner", "tests", str(tmp_path)],
            stdout=text_stdout,
        )
        == 0
    )

    workspace = workspace_stdout.getvalue()
    prime = prime_stdout.getvalue()
    text = text_stdout.getvalue()
    assert workspace.startswith("[search-workspace]")
    assert "|package . name=demo-python role=workspace-root" in workspace
    assert (
        "|package src/pkg name=pkg role=workspace-package surface=source" in workspace
    )
    assert prime.startswith("[search-prime]")
    assert '|dependency D:requests requirement="requests>=2"' in prime
    assert "|owner src/pkg/service.py" in prime
    assert "text:build(owner=" in prime
    assert prime.count("deps:requests") == 1
    assert "symbol:build" not in prime
    assert text.startswith("[search-text] q=build")
    assert "|owner src/pkg/service.py" in text
    assert "|edge O:src/pkg/service.py -test-> O:tests/test_service.py" in text


def test_cli_search_callsite_uses_parser_call_facts(tmp_path: Path) -> None:
    write_search_fixture(tmp_path)
    stdout = io.StringIO()

    exit_code = run_cli(["search", "callsite", "build", str(tmp_path)], stdout=stdout)

    rendered = stdout.getvalue()
    assert exit_code == 0
    assert rendered.startswith("[search-callsite] q=build hit=1")
    assert "|owner tests/test_service.py" in rendered
    assert "|hit path=tests/test_service.py line=4" in rendered
    assert "owner=tests/test_service.py kind=callsite" in rendered
    assert "symbol=build" in rendered


def test_cli_search_public_external_types_uses_public_api_facts(
    tmp_path: Path,
) -> None:
    write_search_fixture(tmp_path)
    stdout = io.StringIO()
    json_stdout = io.StringIO()

    exit_code = run_cli(
        ["search", "public-external-types", "requests", str(tmp_path)],
        stdout=stdout,
    )
    json_exit_code = run_cli(
        ["search", "public-external-types", "requests", "--json", str(tmp_path)],
        stdout=json_stdout,
    )

    rendered = stdout.getvalue()
    assert exit_code == 0
    assert rendered.startswith("[search-public-external-types] q=requests")
    assert "package=requests" in rendered
    assert "|api path=src/pkg/service.py line=6" in rendered
    assert "reason=public-external-type" in rendered
    assert "confidence=direct" in rendered
    assert "|api path=src/pkg/service.py line=9" in rendered
    assert "reason=possible-public-external-type" in rendered
    assert "confidence=possible" in rendered

    packet = json.loads(json_stdout.getvalue())
    assert json_exit_code == 0
    assert packet["method"] == "search/public-external-types"
    assert packet["view"] == "public-external-types"
    assert packet["header"]["fields"]["package"] == "requests"
    assert any(
        hit["reason"] == "public-external-type"
        and hit["fields"]["dependency"] == "requests"
        and hit["fields"]["confidence"] == "direct"
        for hit in packet["hits"]
    )
    assert any(
        hit["reason"] == "possible-public-external-type"
        and hit["fields"]["dependency"] == "requests"
        and hit["fields"]["confidence"] == "possible"
        for hit in packet["hits"]
    )


def test_cli_search_deps_routes_dependency_api_followups(tmp_path: Path) -> None:
    write_search_fixture(tmp_path)
    stdout = io.StringIO()
    json_stdout = io.StringIO()

    exit_code = run_cli(
        ["search", "deps", "requests@2::Session", str(tmp_path)],
        stdout=stdout,
    )
    json_exit_code = run_cli(
        ["search", "deps", "requests@2::Session", "--json", str(tmp_path)],
        stdout=json_stdout,
    )

    rendered = stdout.getvalue()
    assert exit_code == 0
    assert rendered.startswith("[search-deps] q=requests@2::Session")
    assert "package=requests" in rendered
    assert "requestedVersion=2" in rendered
    assert "versionScope=current" in rendered
    assert "api=Session" in rendered
    assert (
        "|next dependency:requests,public-external-types:requests,"
        "api:requests@2::Session,text:Session,tests:Session"
    ) in rendered

    packet = json.loads(json_stdout.getvalue())
    assert json_exit_code == 0
    assert packet["method"] == "search/deps"
    assert packet["header"]["kind"] == "search-deps"
    assert packet["header"]["fields"]["package"] == "requests"
    assert packet["header"]["fields"]["api"] == "Session"
    assert {action["kind"] for action in packet["nextActions"]} >= {
        "dependency",
        "public-external-types",
        "api",
        "text",
        "tests",
    }


def test_cli_search_ingest_groups_rg_output_by_owner(tmp_path: Path) -> None:
    write_search_fixture(tmp_path)
    stdout = io.StringIO()

    exit_code = run_cli(
        ["search", "ingest", str(tmp_path)],
        stdout=stdout,
        stdin="src/pkg/service.py:3:def build(value: str) -> str:\n",
    )

    rendered = stdout.getvalue()
    assert exit_code == 0
    assert rendered.startswith("[search-ingest] source=rg-n hit=1")
    assert "|owner src/pkg/service.py" in rendered
    assert "|hit path=src/pkg/service.py line=3 owner=src/pkg/service.py" in rendered
