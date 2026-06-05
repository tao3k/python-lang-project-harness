"""Top-level Python tree-sitter-compatible query command adapter."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, TextIO

from ._tree_sitter_query_catalog import resolved_tree_sitter_query
from ._tree_sitter_query_model import parse_selector
from ._tree_sitter_query_packet import (
    syntax_query_packet,
    tree_sitter_query_code,
    tree_sitter_query_compact_lines,
)
from ._tree_sitter_query_projection import project_tree_sitter_query

if TYPE_CHECKING:
    from ._cli_args import ProtocolArgs
    from ._model import PythonHarnessReport


def write_tree_sitter_query_response(
    args: ProtocolArgs,
    *,
    report: PythonHarnessReport,
    project_root: Path,
    stdout: TextIO,
) -> None:
    """Write compact or JSON tree-sitter-compatible query results."""

    query = resolved_tree_sitter_query(args)
    terms = list(args.query_set)
    selector = parse_selector(args.selector)
    projection = project_tree_sitter_query(
        report,
        project_root,
        str(query["source"]),
        tuple(query["captures"]),
        terms,
        selector,
    )
    if args.json:
        stdout.write(
            json.dumps(
                syntax_query_packet(
                    project_root=project_root,
                    query=query,
                    terms=terms,
                    selector=selector,
                    code_output=args.code_only,
                    projection=projection,
                ),
                separators=(",", ":"),
            )
        )
        stdout.write("\n")
        return
    if args.code_only:
        stdout.write(tree_sitter_query_code(projection.rows))
        if projection.rows:
            stdout.write("\n")
        return
    stdout.write(tree_sitter_query_compact_lines(query, terms, projection))
    stdout.write("\n")
