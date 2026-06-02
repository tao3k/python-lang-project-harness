"""Execute provider-native Python query protocol commands."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, TextIO

from ._semantic_search_items import (
    owner_item_direct_read_lines,
    owner_item_query_lines,
    owner_item_semantic_query_packet,
)

if TYPE_CHECKING:
    from ._cli_args import ProtocolArgs


def run_query_command(
    args: ProtocolArgs,
    *,
    report: Any,
    project_root: Path,
    stdout: TextIO,
) -> int:
    """Run a parsed query command against parser-owned report facts."""

    owner_path = args.owner_path or ""
    item_query = "|".join(args.query_set)
    packet = owner_item_semantic_query_packet(
        report,
        project_root,
        owner_path,
        item_query,
        output_mode="names" if args.names_only else "code",
        selector=args.selector,
    )
    if args.json:
        stdout.write(json.dumps(packet, separators=(",", ":")))
        stdout.write("\n")
    elif args.code_only:
        stdout.write(
            "\n".join(
                str(match["code"])
                for match in packet["matches"]
                if isinstance(match.get("code"), str)
            )
        )
        stdout.write("\n")
    elif _selector_has_line_range(args.selector, owner_path):
        stdout.write(
            owner_item_direct_read_lines(
                report,
                project_root,
                owner_path,
                item_query,
                args.selector or owner_path,
            )
        )
        stdout.write("\n")
    else:
        stdout.write(
            owner_item_query_lines(
                report,
                project_root,
                owner_path,
                item_query,
                names_only=args.names_only,
            )
        )
        stdout.write("\n")
    return 0


def _selector_has_line_range(selector: str | None, owner_path: str) -> bool:
    if selector is None:
        return False
    normalized = selector.replace("\\", "/").removeprefix("owner:")
    if any(marker in normalized for marker in ("*", "{", "}")):
        return False
    return normalized.startswith(f"{owner_path}:")
