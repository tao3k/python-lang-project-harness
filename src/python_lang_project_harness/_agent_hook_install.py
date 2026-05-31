"""Bridge Python hook profile data into the root semantic-agent-hook runtime."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from ._semantic_language import (
    PYTHON_BINARY,
    PYTHON_LANGUAGE_ID,
    PYTHON_PROVIDER_ID,
    PYTHON_PROVIDER_NAMESPACE,
)

PROFILE_REGISTRY_SCHEMA_ID = (
    "agent.semantic-protocols.semantic-agent-hook-profile-registry"
)
PROFILE_REGISTRY_SCHEMA_VERSION = "1"
HOOK_PROTOCOL_ID = "agent.semantic-protocols.agent-hooks"
HOOK_PROTOCOL_VERSION = "1"


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


def ensure_python_agent_profile_registry(repo_root: Path) -> Path:
    profile_path = python_agent_profile_registry_path(repo_root)
    if profile_path.exists():
        return profile_path
    return write_python_agent_profile_registry(repo_root)


def write_python_agent_profile_registry(repo_root: Path) -> Path:
    profile_path = python_agent_profile_registry_path(repo_root)
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profile_path.write_text(
        json.dumps(python_agent_profile_registry(), indent=2) + "\n",
        encoding="utf-8",
    )
    return profile_path


def python_agent_profile_registry() -> dict[str, Any]:
    return {
        "schemaId": PROFILE_REGISTRY_SCHEMA_ID,
        "schemaVersion": PROFILE_REGISTRY_SCHEMA_VERSION,
        "protocolId": HOOK_PROTOCOL_ID,
        "protocolVersion": HOOK_PROTOCOL_VERSION,
        "projectRoot": ".",
        "profiles": [
            {
                "languageId": PYTHON_LANGUAGE_ID,
                "providerId": PYTHON_PROVIDER_ID,
                "binary": PYTHON_BINARY,
                "namespace": PYTHON_PROVIDER_NAMESPACE,
                "sourceExtensions": [".py", ".pyi"],
                "configFiles": ["pyproject.toml", "setup.cfg", "setup.py"],
                "sourceRoots": ["src", "test", "tests", "packages"],
                "ignoredPathPrefixes": [
                    ".venv",
                    "__pycache__",
                    ".git",
                    ".pytest_cache",
                ],
                "policy": {
                    "blockDirectRead": True,
                    "blockBroadRawSearch": True,
                    "blockAgentSearchJson": True,
                    "requirePrimeBeforeEdit": True,
                },
                "commands": {
                    "prime": {"argv": [PYTHON_BINARY, "search", "prime", "."]},
                    "owner": {
                        "argv": [PYTHON_BINARY, "search", "owner", "{path}", "."]
                    },
                    "text": {
                        "argv": [
                            PYTHON_BINARY,
                            "search",
                            "text",
                            "{query}",
                            "owner",
                            "tests",
                            "--view",
                            "seeds",
                            ".",
                        ],
                    },
                    "ingest": {
                        "argv": [PYTHON_BINARY, "search", "ingest", "."],
                        "stdinMode": "pipe-candidates",
                    },
                    "checkChanged": {
                        "argv": [PYTHON_BINARY, "check", "--changed", "."]
                    },
                },
            }
        ],
    }


def python_agent_profile_registry_path(repo_root: Path) -> Path:
    return repo_root / ".codex" / "semantic-agent-hook" / "profiles.py-harness.json"


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
