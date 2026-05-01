from __future__ import annotations

from python_lang_parser import PythonExportContractKind, parse_python_source


def test_parse_python_source_collects_annotations_assignments_and_exports() -> None:
    report = parse_python_source(
        """
from .api import Runner as PublicRunner

__all__ = ["PublicRunner", "build"]
VALUE: int = 1
cache = {}
_private = "hidden"


def build(name: str) -> PublicRunner:
    current = PublicRunner(name)
    for index, item in enumerate([current]):
        pass
    return current


class Service:
    endpoint: str
""",
        path="exports.py",
    )

    assert report.is_valid
    assert report.has_annotations
    assert report.export_contract.kind == PythonExportContractKind.STATIC
    assert report.export_contract.names == ("PublicRunner", "build")
    assert report.export_candidates == ("PublicRunner", "build")
    assert report.shape is not None
    assert report.shape.top_level_statement_count == 6
    assert report.shape.public_symbol_count == 2
    assert report.shape.public_assignment_count == 2

    symbol_annotations = {
        symbol.qualified_name: symbol.has_annotations for symbol in report.symbols
    }
    assert symbol_annotations == {
        "build": True,
        "Service": True,
    }

    assignments = {
        (assignment.scope, assignment.name): assignment
        for assignment in report.assignments
    }
    assert assignments[("", "__all__")].target_kind == "assign"
    assert assignments[("", "__all__")].value_expression == '["PublicRunner", "build"]'
    assert assignments[("", "VALUE")].target_kind == "annotated_assign"
    assert assignments[("", "VALUE")].value_expression == "1"
    assert assignments[("", "VALUE")].is_public
    assert assignments[("", "VALUE")].is_top_level
    assert assignments[("build", "current")].target_kind == "assign"
    assert not assignments[("build", "current")].is_top_level
    assert assignments[("build", "index")].target_kind == "for"
    assert assignments[("build", "item")].target_kind == "for"
    assert assignments[("Service", "endpoint")].target_kind == "annotated_assign"

    serialized = report.to_dict()
    assert serialized["has_annotations"] is True
    assert serialized["export_contract"]["kind"] == "static"
    assert serialized["export_contract"]["names"] == ["PublicRunner", "build"]
    assert serialized["export_candidates"] == ["PublicRunner", "build"]
    assert serialized["assignments"][0]["name"] == "__all__"


def test_parse_python_source_preserves_explicit_empty_exports() -> None:
    report = parse_python_source(
        """
__all__ = []


class Hidden:
    pass
""",
        path="empty_exports.py",
    )

    assert report.is_valid
    assert report.export_contract.kind == PythonExportContractKind.STATIC
    assert report.export_contract.names == ()
    assert report.export_candidates == ()


def test_parse_python_source_falls_back_for_dynamic_exports() -> None:
    report = parse_python_source(
        """
__all__ = ["Public", exported_name]


class Public:
    pass


class Other:
    pass
""",
        path="dynamic_exports.py",
    )

    assert report.is_valid
    assert report.export_contract.kind == PythonExportContractKind.DYNAMIC
    assert report.export_candidates == ("Other", "Public")
