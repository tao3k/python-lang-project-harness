"""Installed package identity for the Python project harness."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from typing import Final

DISTRIBUTION_NAME: Final = "python-lang-project-harness"


def _installed_version() -> str:
    try:
        return version(DISTRIBUTION_NAME)
    except PackageNotFoundError:
        return "0.0.0+unknown"


__version__: Final = _installed_version()
