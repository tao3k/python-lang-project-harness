from __future__ import annotations

import io
import json
from pathlib import Path

from python_lang_project_harness import run_cli


def test_cli_owner_local_projection_registry_advertises_projection_mode(
    tmp_path: Path,
) -> None:
    stdout = io.StringIO()

    exit_code = run_cli(["agent", "doctor", "--json", str(tmp_path)], stdout=stdout)

    assert exit_code == 0
    payload = json.loads(stdout.getvalue())
    schemas = payload["languages"][0]["schemas"]
    assert any(
        schema["schemaId"] == ("agent.semantic-protocols.semantic-source-location")
        and schema["path"] == "schemas/semantic-source-location.v1.schema.json"
        for schema in schemas
    )
    assert any(
        schema["schemaId"]
        == ("agent.semantic-protocols.semantic-tree-sitter-provenance")
        and schema["path"] == "schemas/semantic-tree-sitter-provenance.v1.schema.json"
        for schema in schemas
    )
    descriptors = payload["languages"][0]["methodDescriptors"]
    owner_local_projection = next(
        descriptor
        for descriptor in descriptors
        if descriptor["method"] == "query/owner-local-projection"
    )
    assert owner_local_projection["input"] == "exact-selector"
    assert owner_local_projection["outputSchemaIds"] == [
        "agent.semantic-protocols.semantic-query-packet",
    ]
    assert owner_local_projection["packetSchemas"] == [
        "semantic-query-packet.v1",
        "semantic-tree-sitter-query.v1",
    ]
    assert owner_local_projection["queryInputForms"] == ["selector"]
    assert owner_local_projection["grammarId"] == "tree-sitter-python"
    assert owner_local_projection["cacheReplay"] is False
    assert "read-packet" not in owner_local_projection["outputModes"]

    owner_items = next(
        descriptor
        for descriptor in descriptors
        if descriptor["method"] == "query/owner-items"
    )
    assert owner_items["packetSchemas"] == [
        "semantic-query-packet.v1",
        "semantic-tree-sitter-query.v1",
    ]
    assert owner_items["grammarId"] == "tree-sitter-python"
    assert owner_items["cacheReplay"] is False
