from __future__ import annotations

import io
import json
import os
from pathlib import Path

from python_lang_project_harness._agent_hooks import run_python_agent_hook


def test_python_agent_hook_delegates_direct_read_to_root_runtime(
    tmp_path: Path,
    monkeypatch,
) -> None:
    log_path = _install_semantic_agent_hook_shim(tmp_path, monkeypatch)
    payload = json.dumps(
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "functions.exec_command",
            "tool_input": {
                "cmd": "sed -n '1,80p' src/tools/semantic_sandtable/receipt_reports.py"
            },
        }
    )
    stdout = io.StringIO()

    exit_code = run_python_agent_hook(
        "pre-tool",
        repo_root=tmp_path,
        stdout=stdout,
        stdin=payload,
    )

    assert exit_code == 0
    response = json.loads(stdout.getvalue())
    assert response["agentHookDecision"]["protocolId"] == (
        "agent.semantic-protocols.agent-hooks"
    )
    assert response["agentHookDecision"]["event"] == "pre-tool"
    profile_path = (
        tmp_path / ".codex" / "semantic-agent-hook" / "profiles.py-harness.json"
    )
    invocations = json.loads(log_path.read_text(encoding="utf-8"))
    assert invocations[0]["argv"] == [
        "hook",
        "--client",
        "codex",
        "pre-tool",
        "--profiles",
        str(profile_path),
    ]
    assert invocations[0]["stdin"] == payload


def _install_semantic_agent_hook_shim(
    tmp_path: Path,
    monkeypatch,
) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log_path = tmp_path / "semantic-agent-hook-invocations.json"
    shim = bin_dir / "semantic-agent-hook"
    shim.write_text(
        "\n".join(
            [
                "#!/usr/bin/env python3",
                "import json, os, pathlib, sys",
                "log_path = pathlib.Path(os.environ['SEMANTIC_AGENT_HOOK_LOG'])",
                "stdin = sys.stdin.read()",
                "entries = json.loads(log_path.read_text()) if log_path.exists() else []",
                "entries.append({'argv': sys.argv[1:], 'cwd': os.getcwd(), 'stdin': stdin})",
                "log_path.write_text(json.dumps(entries, indent=2))",
                "argv = sys.argv[1:]",
                "if argv and argv[0] == 'hook':",
                "    print(json.dumps({'agentHookDecision': {'protocolId': 'agent.semantic-protocols.agent-hooks', 'event': argv[3]}}))",
                "else:",
                "    print('unexpected semantic-agent-hook argv: ' + ' '.join(argv), file=sys.stderr)",
                "    sys.exit(2)",
            ]
        ),
        encoding="utf-8",
    )
    shim.chmod(0o755)
    monkeypatch.setenv("PATH", str(bin_dir) + os.pathsep + os.environ.get("PATH", ""))
    monkeypatch.setenv("SEMANTIC_AGENT_HOOK_LOG", str(log_path))
    return log_path
