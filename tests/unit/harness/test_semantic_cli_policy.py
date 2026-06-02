from __future__ import annotations

import io
import json
from pathlib import Path

from python_lang_project_harness._cli import run_cli


def test_cli_agent_doctor_json_advertises_policy_search(
    tmp_path: Path,
) -> None:
    stdout = io.StringIO()
    exit_code = run_cli(["agent", "doctor", "--json", str(tmp_path)], stdout=stdout)
    payload = json.loads(stdout.getvalue())
    assert exit_code == 0
    registration = payload["languages"][0]
    assert "search/policy" in registration["methods"]
    assert any(
        schema["schemaId"] == "agent.semantic-protocols.semantic-handle"
        and schema["path"] == "schemas/semantic-handle.v1.schema.json"
        for schema in registration["schemas"]
    )
    assert any(
        descriptor["method"] == "search/policy"
        and descriptor["acceptedPipes"] == ["owner", "tests"]
        and descriptor["outputSchemaIds"]
        == [
            "agent.semantic-protocols.semantic-search-packet",
            "agent.semantic-protocols.semantic-handle",
        ]
        and any(
            capability["name"] == "python-project-policy-rule-handle-search"
            for capability in descriptor["capabilities"]
        )
        for descriptor in registration["methodDescriptors"]
    )


def test_cli_search_policy_renders_semantic_handles(
    tmp_path: Path,
) -> None:
    seeds_stdout = io.StringIO()
    compact_stdout = io.StringIO()
    json_stdout = io.StringIO()
    assert (
        run_cli(
            [
                "search",
                "policy",
                "PY-PROJ-R001",
                "owner",
                "tests",
                "--view",
                "seeds",
                str(tmp_path),
            ],
            stdout=seeds_stdout,
        )
        == 0
    )
    assert (
        run_cli(
            ["search", "policy", "src layout", "owner", "tests", str(tmp_path)],
            stdout=compact_stdout,
        )
        == 0
    )
    assert (
        run_cli(
            [
                "search",
                "policy",
                "PY-AGENT-R008",
                "owner",
                "tests",
                "--json",
                str(tmp_path),
            ],
            stdout=json_stdout,
        )
        == 0
    )
    seeds = seeds_stdout.getvalue()
    compact = compact_stdout.getvalue()
    packet = json.loads(json_stdout.getvalue())
    assert seeds.startswith("[search-policy] q=PY-PROJ-R001")
    assert "|query PY-PROJ-R001 status=hit hit=1 selected=1" in seeds
    assert "|handle PY-PROJ-R001 kind=policy-rule source=provider-policy" in seeds
    assert "|seed owner:src/python_lang_project_harness/_project_policy_catalog.py" in seeds
    assert "tests/unit/harness/project_policy/test_layout.py" in seeds
    assert "|handle PY-PROJ-R001 kind=policy-rule source=provider-policy" in compact
    assert "title=\"Python project should use src layout\"" in compact
    assert "implementation=None" not in compact
    assert packet["view"] == "policy"
    assert packet["semanticHandles"][0]["id"] == "PY-AGENT-R008"
    assert packet["semanticHandles"][0]["ownerPath"] == (
        "src/python_lang_project_harness/_agent_policy_catalog.py"
    )
    assert "tests/unit/harness/test_agent_policy.py" in packet["semanticHandles"][0][
        "testPaths"
    ]
