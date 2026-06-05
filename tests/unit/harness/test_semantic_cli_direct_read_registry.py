from __future__ import annotations

import io
import json
from pathlib import Path

from python_lang_project_harness import run_cli


def test_cli_direct_read_registry_advertises_read_packet_mode(
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
    direct_read = next(
        descriptor
        for descriptor in descriptors
        if descriptor["method"] == "query/direct-source-read"
    )
    assert direct_read["outputSchemaIds"] == [
        "agent.semantic-protocols.semantic-query-packet",
        "agent.semantic-protocols.semantic-read-packet",
    ]
    assert "read-packet" in direct_read["outputModes"]
