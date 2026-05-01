from __future__ import annotations

from snapshot_support import assert_snapshot

from python_lang_parser import (
    PythonDiagnosticSeverity,
    PythonModuleReport,
    SourceLocation,
)
from python_lang_project_harness import (
    PythonHarnessFinding,
    PythonHarnessReport,
    render_python_lang_harness,
    render_python_lang_harness_json,
)


def test_compact_text_render_matches_snapshot() -> None:
    rendered = render_python_lang_harness(_snapshot_report())

    assert_snapshot("python_project_harness_compact_text", rendered)


def test_json_render_matches_snapshot() -> None:
    rendered = render_python_lang_harness_json(_snapshot_report())

    assert_snapshot("python_project_harness_json", rendered)


def _snapshot_report() -> PythonHarnessReport:
    source_path = "$TEMP/src/service.py"
    return PythonHarnessReport(
        modules=(
            PythonModuleReport(
                path=source_path,
                module_docstring="Service helpers.",
            ),
        ),
        findings=(
            PythonHarnessFinding(
                rule_id="PY-MOD-R002",
                pack_id="python.modern_design",
                severity=PythonDiagnosticSeverity.WARNING,
                title="Library module uses bare print",
                summary="$TEMP/src/service.py calls bare print().",
                location=SourceLocation(source_path, 5, 4),
                requirement=(
                    "Use a logger, returned value, or explicit test assertion "
                    "instead of bare `print` in library modules."
                ),
                source_line='    print("debug")',
                label="replace bare print with a project-owned reporting surface",
                labels={"domain": "modern-python", "language": "python"},
            ),
        ),
        root_paths=("$TEMP/src", "$TEMP/tests"),
    )
