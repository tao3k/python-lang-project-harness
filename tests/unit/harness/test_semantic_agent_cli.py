"""Semantic agent CLI tests for the Python harness provider."""

from __future__ import annotations

import io
import json
import os
from pathlib import Path

import pytest

from python_lang_project_harness import run_cli


def test_cli_agent_install_delegates_to_semantic_agent_hook(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    log_path = _install_semantic_agent_hook_shim(tmp_path, monkeypatch)
    stdout = io.StringIO()

    exit_code = run_cli(
        ["agent", "install", "--client", "codex", str(tmp_path)],
        stdout=stdout,
    )

    config = (tmp_path / ".codex" / "config.toml").read_text(encoding="utf-8")
    profile_path = (
        tmp_path / ".codex" / "semantic-agent-hook" / "profiles.py-harness.json"
    )
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert stdout.getvalue().startswith("[agent-install] client=codex profiles=")
    assert "# BEGIN semantic-agent-hook agent hooks" in config
    assert "# BEGIN py-harness agent hooks" not in config
    assert profile["protocolId"] == "agent.semantic-protocols.agent-hooks"
    assert profile["profiles"][0]["languageId"] == "python"
    assert profile["profiles"][0]["providerId"] == "py-harness"
    assert (
        profile["profiles"][0]["commands"]["ingest"]["stdinMode"] == "pipe-candidates"
    )
    invocations = json.loads(log_path.read_text(encoding="utf-8"))
    assert invocations[0]["argv"] == [
        "install",
        "--client",
        "codex",
        "--profiles",
        str(profile_path),
        str(tmp_path.resolve()),
    ]


def test_cli_agent_hook_delegates_to_semantic_agent_hook(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    log_path = _install_semantic_agent_hook_shim(tmp_path, monkeypatch)
    stdout = io.StringIO()
    payload = json.dumps({"tool_name": "Read", "tool_input": {"path": "src/app.py"}})

    exit_code = run_cli(
        ["agent", "hook", "--client", "codex", "pre-tool", str(tmp_path)],
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


def test_cli_agent_install_reports_missing_semantic_agent_hook(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stdout = io.StringIO()
    stderr = io.StringIO()
    monkeypatch.setenv("PATH", "")

    exit_code = run_cli(
        ["agent", "install", "--client", "codex", str(tmp_path)],
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 3
    assert stdout.getvalue() == ""
    assert "semantic-agent-hook binary is required" in stderr.getvalue()


def _install_semantic_agent_hook_shim(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
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
                "if argv and argv[0] == 'install':",
                "    profile_path = pathlib.Path(argv[argv.index('--profiles') + 1])",
                "    root = pathlib.Path(argv[-1])",
                "    json.loads(profile_path.read_text())",
                "    (root / '.codex').mkdir(parents=True, exist_ok=True)",
                "    (root / '.codex' / 'config.toml').write_text('# BEGIN semantic-agent-hook agent hooks\\n')",
                "    print('[agent-install] client=codex profiles=.codex/semantic-agent-hook/profiles.json config=.codex/config.toml binary=.codex/semantic-agent-hook/bin/semantic-agent-hook mode=updated')",
                "elif argv and argv[0] == 'hook':",
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
