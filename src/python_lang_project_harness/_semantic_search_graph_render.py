"""Delegate Python compact graph rendering to the shared protocol binary."""

from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Callable
from typing import Any

DEFAULT_GRAPH_SEED_LIMIT = 8
SEMANTIC_AGENT_PROTOCOL_BIN_ENV = "SEMANTIC_AGENT_PROTOCOL_BIN"


class CompactGraphRenderError(RuntimeError):
    """Raised when the shared compact graph renderer cannot produce output."""


def compact_graph_seed_packet_text(
    packet: dict[str, Any],
    render_fields: Callable[[dict[str, Any]], str],
) -> str:
    del render_fields
    return render_compact_graph_packet(packet, seed_limit=DEFAULT_GRAPH_SEED_LIMIT)


def render_compact_graph_packet(
    packet: dict[str, Any],
    *,
    seed_limit: int = DEFAULT_GRAPH_SEED_LIMIT,
) -> str:
    command = [
        os.environ.get(SEMANTIC_AGENT_PROTOCOL_BIN_ENV, "asp"),
        "graph",
        "render",
        "--packet",
        "-",
        "--view",
        "seeds",
        "--seeds",
        str(seed_limit),
    ]
    try:
        completed = subprocess.run(
            command,
            input=json.dumps(packet, separators=(",", ":")),
            text=True,
            capture_output=True,
            check=True,
        )
    except FileNotFoundError as exc:
        raise CompactGraphRenderError(
            "asp graph renderer not found; "
            f"set {SEMANTIC_AGENT_PROTOCOL_BIN_ENV} or install "
            "asp on PATH"
        ) from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip()
        detail = f": {stderr}" if stderr else ""
        raise CompactGraphRenderError(
            f"asp graph render failed with exit code {exc.returncode}{detail}"
        ) from exc
    return completed.stdout
