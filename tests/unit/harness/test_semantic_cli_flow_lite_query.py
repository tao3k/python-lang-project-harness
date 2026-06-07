"""Flow-lite query compatibility tests for the Python semantic CLI."""

from __future__ import annotations

import io
import json
from pathlib import Path

from python_lang_project_harness import run_cli


def test_cli_query_flow_lite_renders_native_bounded_frontier(tmp_path: Path) -> None:
    _write_flow_lite_fixture(tmp_path)
    stdout = io.StringIO()

    exit_code = run_cli(
        _flow_lite_query_args(tmp_path),
        stdout=stdout,
    )

    rendered = stdout.getvalue()
    assert exit_code == 0
    assert "[query-flow-lite]" in rendered
    assert "lang=python catalog=flow-lite" in rendered
    assert "S=source:call(payload_string)@src/flow.py:9!code" in rendered
    assert "K=sink:constructs(ToolAction)@src/flow.py:10!code" in rendered
    assert "P=path:bounded(S->K)!flow" in rendered
    assert "S>{K:flows-to}" in rendered
    assert "confidence=bounded sourceAuthority=native-parser" in rendered
    assert "frontier=S.code,K.code,P.flow" in rendered
    assert "unknown query option" not in rendered


def test_cli_query_flow_lite_json_emits_bounded_packet(tmp_path: Path) -> None:
    _write_flow_lite_fixture(tmp_path)
    stdout = io.StringIO()

    exit_code = run_cli(
        _flow_lite_query_args(tmp_path, "--json"),
        stdout=stdout,
    )

    assert exit_code == 0
    packet = json.loads(stdout.getvalue())
    assert packet["schemaId"] == "agent.semantic-protocols.semantic-flow-lite"
    assert packet["languageId"] == "python"
    assert packet["providerId"] == "py-harness"
    assert packet["flowKind"] == "local-source-sink"
    assert packet["sourceAuthority"] == "native-parser"
    assert packet["executionBackend"] == "native-parser"
    assert packet["adapterMode"] == "native-projection"
    assert packet["confidence"] == "bounded"
    assert packet["ownerPath"] == "src/flow.py"
    assert len(packet["path"]) == 3
    assert packet["path"][0]["relation"] == "source"
    assert packet["path"][1]["relation"] == "sink"
    assert packet["path"][2]["relation"] == "flows-to"
    assert packet["omissions"] == []
    assert packet["fields"]["rawSourceStored"] is False
    assert packet["fields"]["where"]["scope.fn"] == "collect_tool_actions"


def test_cli_query_flow_lite_rejects_code_output_and_open_where_key(
    tmp_path: Path,
) -> None:
    code_stdout = io.StringIO()
    code_stderr = io.StringIO()

    code_exit = run_cli(
        _flow_lite_query_args(tmp_path, "--code"),
        stdout=code_stdout,
        stderr=code_stderr,
    )

    assert code_exit == 2
    assert "locator/provenance surface" in code_stderr.getvalue()

    open_where_stdout = io.StringIO()
    open_where_stderr = io.StringIO()
    open_where_exit = run_cli(
        [
            "query",
            "--catalog",
            "flow-lite",
            "--where",
            "source.call=payload sink.constructs=Action scope.fn=collect guard.eq=is_safe",
            str(tmp_path),
        ],
        stdout=open_where_stdout,
        stderr=open_where_stderr,
    )

    assert open_where_exit == 2
    assert (
        "unsupported flow-lite --where key `guard.eq`" in open_where_stderr.getvalue()
    )


def _flow_lite_query_args(project_root: Path, *extra_args: str) -> list[str]:
    return [
        "query",
        "--catalog",
        "flow-lite",
        "--where",
        "source.call=payload_string sink.constructs=ToolAction scope.fn=collect_tool_actions",
        *extra_args,
        str(project_root),
    ]


def _write_flow_lite_fixture(project_root: Path) -> None:
    source_dir = project_root / "src"
    source_dir.mkdir()
    (source_dir / "flow.py").write_text(
        "\n".join(
            [
                "class ToolAction:",
                "    def __init__(self, payload: str) -> None:",
                "        self.payload = payload",
                "",
                "def payload_string(value: str) -> str:",
                "    return value.strip()",
                "",
                "def collect_tool_actions(value: str) -> list[ToolAction]:",
                "    payload = payload_string(value)",
                "    return [ToolAction(payload)]",
            ]
        ),
        encoding="utf-8",
    )
