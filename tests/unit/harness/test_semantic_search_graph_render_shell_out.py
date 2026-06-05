from __future__ import annotations

import json
from pathlib import Path

import pytest

from python_lang_project_harness._semantic_search_graph_render import (
    SEMANTIC_AGENT_PROTOCOL_BIN_ENV,
    CompactGraphRenderError,
    render_compact_graph_packet,
)


def test_compact_graph_renderer_shells_out_to_protocol_bin(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    argv_path = tmp_path / "argv.txt"
    stdin_path = tmp_path / "stdin.json"
    protocol_bin = tmp_path / "semantic-agent-protocol"
    protocol_bin.write_text(
        "#!/bin/sh\n"
        'printf "%s\\n" "$@" > "$ASLP_ARGV_PATH"\n'
        'cat > "$ASLP_STDIN_PATH"\n'
        'printf "[search-fzf] q=test\\n"\n'
    )
    protocol_bin.chmod(0o755)
    monkeypatch.setenv(SEMANTIC_AGENT_PROTOCOL_BIN_ENV, str(protocol_bin))
    monkeypatch.setenv("ASLP_ARGV_PATH", str(argv_path))
    monkeypatch.setenv("ASLP_STDIN_PATH", str(stdin_path))

    packet = {"header": {"kind": "search-fzf"}}

    output = render_compact_graph_packet(packet, seed_limit=3)

    assert output == "[search-fzf] q=test\n"
    assert argv_path.read_text().splitlines() == [
        "graph",
        "render",
        "--packet",
        "-",
        "--view",
        "seeds",
        "--seeds",
        "3",
    ]
    assert json.loads(stdin_path.read_text()) == packet


def test_compact_graph_renderer_missing_bin_does_not_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        SEMANTIC_AGENT_PROTOCOL_BIN_ENV,
        str(tmp_path / "missing-semantic-agent-protocol"),
    )

    with pytest.raises(CompactGraphRenderError, match="not found"):
        render_compact_graph_packet({"header": {"kind": "search-fzf"}})
