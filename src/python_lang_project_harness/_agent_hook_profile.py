"""Python-owned semantic-agent-hook profile descriptor."""

from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path
from typing import Any

PROFILE_RESOURCE = "semantic-agent-hook-profile.py-harness.v1.json"


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
    profile_text = (
        files("python_lang_project_harness")
        .joinpath(PROFILE_RESOURCE)
        .read_text(encoding="utf-8")
    )
    return json.loads(profile_text)


def python_agent_profile_registry_path(repo_root: Path) -> Path:
    return repo_root / ".codex" / "semantic-agent-hook" / "profiles.py-harness.json"
