"""Bridge Python agent hook commands into the root semantic-agent-hook runtime."""

from __future__ import annotations

import subprocess
from pathlib import Path

from ._agent_hook_profile import (
    ensure_python_agent_profile_registry,
    write_python_agent_profile_registry,
)


def install_python_agent_assets(repo_root: Path) -> str:
    profile_path = write_python_agent_profile_registry(repo_root)
    return run_semantic_agent_hook(
        [
            "install",
            "--client",
            "codex",
            "--profiles",
            str(profile_path),
            str(repo_root),
        ],
        cwd=repo_root,
    )


def run_python_agent_hook_event(
    hook_event: str,
    *,
    repo_root: Path,
    stdin: str,
) -> str:
    profile_path = ensure_python_agent_profile_registry(repo_root)
    return run_semantic_agent_hook(
        ["hook", "--client", "codex", hook_event, "--profiles", str(profile_path)],
        cwd=repo_root,
        stdin=stdin,
    )


def run_semantic_agent_hook(
    args: list[str],
    *,
    cwd: Path,
    stdin: str = "",
) -> str:
    try:
        completed = subprocess.run(
            [semantic_agent_hook_binary(cwd), *args],
            cwd=cwd,
            input=stdin,
            text=True,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError as error:
        raise RuntimeError(
            "semantic-agent-hook binary is required for Codex hook install/runtime"
        ) from error
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"semantic-agent-hook failed: {detail}")
    return completed.stdout


def semantic_agent_hook_binary(repo_root: Path) -> str:
    local_binary = (
        repo_root / ".codex" / "semantic-agent-hook" / "bin" / "semantic-agent-hook"
    )
    if local_binary.is_file():
        return str(local_binary)
    return "semantic-agent-hook"
