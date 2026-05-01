from __future__ import annotations

from python_lang_parser import PythonDiagnosticSeverity, parse_python_source


def test_parse_python_source_reports_syntax_error_as_diagnostic() -> None:
    report = parse_python_source("def broken(:\n    pass\n", path="broken.py")

    assert not report.is_valid
    assert len(report.diagnostics) == 1
    diagnostic = report.diagnostics[0]
    assert diagnostic.code == "python.syntax.invalid"
    assert diagnostic.severity == PythonDiagnosticSeverity.ERROR
    assert diagnostic.location.path == "broken.py"
    assert diagnostic.location.line == 1
    assert diagnostic.source_line == "def broken(:"
    assert report.source_line(1) == "def broken(:"


def test_parse_python_source_reports_compile_invalid_scope_as_diagnostic() -> None:
    report = parse_python_source("return 1\n", path="bad_scope.py")

    assert not report.is_valid
    assert len(report.diagnostics) == 1
    diagnostic = report.diagnostics[0]
    assert diagnostic.code == "python.compile.invalid"
    assert diagnostic.severity == PythonDiagnosticSeverity.ERROR
    assert diagnostic.location.path == "bad_scope.py"
    assert "outside function" in diagnostic.message
