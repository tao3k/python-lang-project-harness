from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, Any

from snapshot_support import normalize_temp_root
from syrupy.extensions.json import JSONSnapshotExtension
from syrupy.extensions.single_file import SingleFileSnapshotExtension, WriteMode

from python_lang_project_harness import (
    render_python_lang_harness,
    run_python_lang_harness,
)

if TYPE_CHECKING:
    from syrupy.assertion import SnapshotAssertion

    from python_lang_project_harness import PythonHarnessReport


_SCENARIO = (
    Path(__file__).parent / "scenarios" / "software_criteria" / "control_flow_v1"
)


class _ScenarioJsonSnapshotExtension(JSONSnapshotExtension):
    @classmethod
    def dirname(cls, *, test_location: Any) -> str:
        return str(_SCENARIO / "expect")

    @classmethod
    def get_file_basename(cls, *, test_location: Any, index: object) -> str:
        if isinstance(index, str):
            return index
        return super().get_file_basename(test_location=test_location, index=index)


class _ScenarioTextSnapshotExtension(SingleFileSnapshotExtension):
    _write_mode = WriteMode.TEXT
    file_extension = "txt"

    @classmethod
    def dirname(cls, *, test_location: Any) -> str:
        return str(_SCENARIO / "expect")

    @classmethod
    def get_file_basename(cls, *, test_location: Any, index: object) -> str:
        if isinstance(index, str):
            return index
        return super().get_file_basename(test_location=test_location, index=index)


def test_py_software_criterion_control_flow_v1_snapshot(
    tmp_path: Path,
    snapshot: SnapshotAssertion,
) -> None:
    _copy_inputs(_SCENARIO / "inputs", tmp_path)

    report = run_python_lang_harness([tmp_path / "criterion.py"])
    filtered = _filter_software_criterion_findings(report)
    findings = [
        {
            "rule_id": finding.rule_id,
            "summary": finding.summary,
            "line": finding.location.line,
            "label": finding.label,
            "softwareCriteria": finding.labels.get("softwareCriteria"),
        }
        for finding in filtered.findings
    ]
    rendered = normalize_temp_root(render_python_lang_harness(filtered), tmp_path)

    assert {finding["softwareCriteria"] for finding in findings} == {
        "control-flow.decision-stack",
        "control-flow.traversal-knot",
        "control-flow.literal-dispatch-chain",
        "control-flow.broad-linear-phase",
        "native-idiom.manual-transform-loop",
    }
    assert (
        snapshot(name="findings", extension_class=_ScenarioJsonSnapshotExtension)
        == findings
    )
    assert (
        snapshot(name="rendered", extension_class=_ScenarioTextSnapshotExtension)
        == rendered
    )


def _copy_inputs(source_dir: Path, destination_dir: Path) -> None:
    for source in source_dir.rglob("*"):
        if source.is_dir():
            continue
        destination = destination_dir / source.relative_to(source_dir)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")


def _filter_software_criterion_findings(
    report: PythonHarnessReport,
) -> PythonHarnessReport:
    return replace(
        report,
        findings=tuple(
            finding
            for finding in report.findings
            if finding.rule_id in {"PY-AGENT-R009", "PY-AGENT-R010", "PY-AGENT-R011"}
        ),
    )
