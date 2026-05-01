from __future__ import annotations

from pathlib import Path

from python_lang_parser import PythonDiagnosticSeverity
from python_lang_project_harness import (
    default_python_harness_config,
    python_agent_policy_rules,
    python_modern_design_rules,
    python_modularity_rules,
    python_project_policy_rules,
    python_rule_pack_descriptors,
    python_syntax_rules,
    python_test_layout_rules,
    render_python_lang_harness,
    run_python_project_harness,
)

_PROJECT_ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "pyproject.toml").exists() and (parent / "src").exists()
)
_SNAPSHOT_ROOT = _PROJECT_ROOT / "tests" / "unit" / "snapshots"
_RULE_CATALOG_DOC = _PROJECT_ROOT / "docs" / "03_features" / "201_rule_catalog.md"
_EXPECTED_RULE_SNAPSHOT_FILES = {
    "unit_test__agent_policy_snapshot__py_agent_r001_module_intent.snap",
    "unit_test__agent_policy_snapshot__py_agent_r002_callable_annotations.snap",
    "unit_test__agent_policy_snapshot__py_agent_r003_callable_conflict.snap",
    "unit_test__agent_policy_snapshot__py_agent_r004_repeated_namespace.snap",
    "unit_test__agent_policy_snapshot__py_agent_r005_type_conflict.snap",
    "unit_test__agent_policy_snapshot__py_agent_r006_value_conflict.snap",
    "unit_test__policy_snapshot__py_mod_r001_wildcard_import.snap",
    "unit_test__policy_snapshot__py_mod_r002_bare_print.snap",
    "unit_test__policy_snapshot__py_mod_r003_facade_all.snap",
    "unit_test__policy_snapshot__py_mod_r004_breakpoint.snap",
    "unit_test__policy_snapshot__py_mod_r006_module_bloat.snap",
    "unit_test__policy_snapshot__py_proj_r001_src_layout.snap",
    "unit_test__policy_snapshot__py_proj_r002_declared_package.snap",
    "unit_test__policy_snapshot__py_proj_r003_py_typed.snap",
    "unit_test__policy_snapshot__py_proj_r004_typed_annotations.snap",
    "unit_test__policy_snapshot__py_proj_r005_project_name.snap",
    "unit_test__policy_snapshot__py_proj_r006_requires_python.snap",
    "unit_test__policy_snapshot__py_proj_r007_build_requires.snap",
    "unit_test__policy_snapshot__py_test_r001_root_pytest.snap",
    "unit_test__policy_snapshot__py_test_r002_unexpected_root.snap",
    "unit_test__policy_snapshot__py_test_r003_unit_bloat.snap",
    "unit_test__policy_snapshot__python_compile_invalid.snap",
    "unit_test__policy_snapshot__python_syntax_invalid.snap",
}


def test_default_policy_blocks_only_warning_and_error() -> None:
    config = default_python_harness_config()

    assert config.blocking_severities == {
        PythonDiagnosticSeverity.ERROR,
        PythonDiagnosticSeverity.WARNING,
    }


def test_agent_policy_rules_are_non_blocking_advice() -> None:
    assert {rule.severity for rule in python_agent_policy_rules()} == {
        PythonDiagnosticSeverity.INFO
    }


def test_rule_pack_descriptors_expose_default_execution_order() -> None:
    descriptors = python_rule_pack_descriptors()

    assert [descriptor.id for descriptor in descriptors] == [
        "python.syntax",
        "python.project_policy",
        "python.modern_design",
        "python.modularity",
        "python.test_layout",
        "python.agent_policy",
    ]
    assert [descriptor.default_mode for descriptor in descriptors] == [
        "blocking",
        "blocking",
        "blocking",
        "blocking",
        "blocking",
        "advisory",
    ]
    assert {descriptor.version for descriptor in descriptors} == {"v1"}
    assert all("python" in descriptor.domains for descriptor in descriptors)


def test_rule_catalogs_expose_stable_rule_ids() -> None:
    assert [rule.rule_id for rule in python_syntax_rules()] == [
        "python.syntax.invalid",
        "python.compile.invalid",
    ]
    assert [rule.rule_id for rule in python_project_policy_rules()] == [
        "PY-PROJ-R001",
        "PY-PROJ-R002",
        "PY-PROJ-R003",
        "PY-PROJ-R004",
        "PY-PROJ-R005",
        "PY-PROJ-R006",
        "PY-PROJ-R007",
    ]
    assert [rule.rule_id for rule in python_modern_design_rules()] == [
        "PY-MOD-R001",
        "PY-MOD-R002",
        "PY-MOD-R003",
        "PY-MOD-R004",
    ]
    assert [rule.rule_id for rule in python_modularity_rules()] == ["PY-MOD-R006"]
    assert [rule.rule_id for rule in python_agent_policy_rules()] == [
        "PY-AGENT-R001",
        "PY-AGENT-R002",
        "PY-AGENT-R003",
        "PY-AGENT-R004",
        "PY-AGENT-R005",
        "PY-AGENT-R006",
    ]
    assert [rule.rule_id for rule in python_test_layout_rules()] == [
        "PY-TEST-R001",
        "PY-TEST-R002",
        "PY-TEST-R003",
    ]


def test_rule_catalogs_keep_default_severities_aligned() -> None:
    assert {rule.severity for rule in python_syntax_rules()} == {
        PythonDiagnosticSeverity.ERROR
    }
    assert {rule.severity for rule in python_project_policy_rules()} == {
        PythonDiagnosticSeverity.WARNING
    }
    assert {rule.severity for rule in python_modern_design_rules()} == {
        PythonDiagnosticSeverity.WARNING
    }
    assert {rule.severity for rule in python_modularity_rules()} == {
        PythonDiagnosticSeverity.WARNING
    }
    assert {rule.severity for rule in python_test_layout_rules()} == {
        PythonDiagnosticSeverity.WARNING
    }
    assert {rule.severity for rule in python_agent_policy_rules()} == {
        PythonDiagnosticSeverity.INFO
    }


def test_rule_catalog_doc_lists_every_default_rule() -> None:
    document = _RULE_CATALOG_DOC.read_text(encoding="utf-8")

    for rule_id in _all_default_rule_ids():
        assert f"`{rule_id}`" in document, rule_id


def test_policy_snapshots_cover_every_catalog_rule() -> None:
    snapshot_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(_SNAPSHOT_ROOT.glob("*.snap"))
    )

    for rule_id in _all_default_rule_ids():
        assert f"[{rule_id}]" in snapshot_text, rule_id


def test_rule_snapshot_files_have_no_stale_policy_baselines() -> None:
    actual_rule_snapshots = {
        path.name
        for pattern in (
            "unit_test__agent_policy_snapshot__*.snap",
            "unit_test__policy_snapshot__*.snap",
        )
        for path in _SNAPSHOT_ROOT.glob(pattern)
    }

    assert actual_rule_snapshots == _EXPECTED_RULE_SNAPSHOT_FILES


def test_project_is_clean_under_its_own_harness() -> None:
    report = run_python_project_harness(_PROJECT_ROOT)
    rendered = render_python_lang_harness(report)

    assert report.is_clean, rendered
    assert "No blocking issues found." in rendered


def test_harness_policy_does_not_parse_python_source_directly() -> None:
    harness_sources = sorted(
        (_PROJECT_ROOT / "src" / "python_lang_project_harness").glob("*.py")
    )

    for path in harness_sources:
        source = path.read_text(encoding="utf-8")
        assert "import ast" not in source, path
        assert "import tokenize" not in source, path
        assert "ast.parse" not in source, path
        assert "tokenize." not in source, path


def test_harness_semantic_roles_use_parser_symbol_helpers() -> None:
    harness_sources = sorted(
        (_PROJECT_ROOT / "src" / "python_lang_project_harness").glob("*.py")
    )
    for path in harness_sources:
        if path.name == "__init__.py":
            continue
        source = path.read_text(encoding="utf-8")
        assert "PythonSymbolKind" not in source, path

    test_bloat = (
        _PROJECT_ROOT / "src" / "python_lang_project_harness" / "_test_layout_bloat.py"
    ).read_text(encoding="utf-8")
    agent_policy = (
        _PROJECT_ROOT / "src" / "python_lang_project_harness" / "_agent_policy.py"
    ).read_text(encoding="utf-8")
    typed_policy = (
        _PROJECT_ROOT
        / "src"
        / "python_lang_project_harness"
        / "_project_policy_typed.py"
    ).read_text(encoding="utf-8")
    namespace_index = (
        _PROJECT_ROOT
        / "src"
        / "python_lang_project_harness"
        / "_agent_namespace_index.py"
    ).read_text(encoding="utf-8")

    assert "python_symbol_is_test_function(" in test_bloat
    assert 'symbol.name.startswith("test_")' not in test_bloat
    assert "python_symbol_is_public_callable(" in agent_policy
    assert "python_module_has_public_symbol_surface(" in agent_policy
    assert "python_symbol_is_public_class(" in typed_policy
    assert "python_symbol_is_public_callable_boundary(" in typed_policy
    assert "python_module_has_public_surface(" in typed_policy
    assert "symbol.is_public" not in typed_policy
    assert "python_symbol_is_callable(" in namespace_index
    assert "python_symbol_is_class(" in namespace_index
    assert "python_symbol_is_public_top_level(" in namespace_index
    assert "python_assignment_is_public_top_level(" in namespace_index
    assert "symbol.is_top_level" not in namespace_index
    assert "symbol.is_public" not in namespace_index
    assert "assignment.is_top_level" not in namespace_index
    assert "assignment.is_public" not in namespace_index


def test_agent_namespace_policy_uses_parser_module_identity_helpers() -> None:
    source = (
        _PROJECT_ROOT / "src" / "python_lang_project_harness" / "_agent_namespace.py"
    ).read_text(encoding="utf-8")

    assert "python_module_namespace_parts(" in source
    assert "relative_to(" not in source
    assert "with_suffix(" not in source


def test_python_semantic_policy_uses_parser_name_helpers() -> None:
    typed_policy = (
        _PROJECT_ROOT
        / "src"
        / "python_lang_project_harness"
        / "_project_policy_typed.py"
    ).read_text(encoding="utf-8")
    modern_design = (
        _PROJECT_ROOT / "src" / "python_lang_project_harness" / "_modern_design.py"
    ).read_text(encoding="utf-8")

    assert "python_symbol_is_public_class(" in typed_policy
    assert "_name_is_public" not in typed_policy
    assert "python_module_is_package_init(" in modern_design
    assert 'name != "__init__.py"' not in modern_design


def test_test_layout_python_source_lines_use_parser_reports() -> None:
    layout = (
        _PROJECT_ROOT / "src" / "python_lang_project_harness" / "_test_layout.py"
    ).read_text(encoding="utf-8")
    entries = (
        _PROJECT_ROOT
        / "src"
        / "python_lang_project_harness"
        / "_test_layout_entries.py"
    ).read_text(encoding="utf-8")

    assert "tests_root_entry_findings(tests_dir, pack_id, modules)" in layout
    assert 'if path.suffix == ".py":' in entries
    assert "return report.source_line(line)" in entries


def _all_default_rule_ids() -> tuple[str, ...]:
    return tuple(
        rule.rule_id
        for rules in (
            python_syntax_rules(),
            python_project_policy_rules(),
            python_modern_design_rules(),
            python_modularity_rules(),
            python_agent_policy_rules(),
            python_test_layout_rules(),
        )
        for rule in rules
    )
