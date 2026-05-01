"""Module entrypoint for `python -m python_lang_project_harness`."""

from __future__ import annotations

from ._cli import run_cli_from_env

raise SystemExit(run_cli_from_env())
