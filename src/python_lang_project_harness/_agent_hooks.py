"""Python agent hook facade."""

from __future__ import annotations

from pathlib import Path
from typing import TextIO

from ._agent_hook_install import (
    install_python_agent_assets,
    run_python_agent_hook_event,
)
from ._agent_hook_profile import (
    python_agent_profile_registry,
    python_agent_profile_registry_path,
    write_python_agent_profile_registry,
)

__all__ = [
    "install_python_agent_assets",
    "python_agent_profile_registry",
    "python_agent_profile_registry_path",
    "run_python_agent_hook",
    "write_python_agent_profile_registry",
]


def run_python_agent_hook(
    hook_event: str | None,
    *,
    repo_root: Path,
    stdout: TextIO,
    stdin: str | None = None,
) -> int:
    if hook_event is None:
        return 0
    stdout.write(
        run_python_agent_hook_event(
            hook_event,
            repo_root=repo_root,
            stdin="" if stdin is None else stdin,
        )
    )
    return 0
