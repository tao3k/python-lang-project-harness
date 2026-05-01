from __future__ import annotations

from python_lang_parser import parse_python_source, python_reasoning_tree_facts


def test_python_reasoning_tree_detects_module_package_owner_shadow() -> None:
    facts = python_reasoning_tree_facts(
        (
            parse_python_source(
                '"""Domain module."""\n', path="/repo/src/pkg/domain.py"
            ),
            parse_python_source(
                '"""Domain package."""\n',
                path="/repo/src/pkg/domain/__init__.py",
            ),
        ),
        import_roots=("/repo/src",),
        project_root="/repo",
    )

    assert [item.to_dict() for item in facts.shadowed_module_sources] == [
        {
            "module_path": "/repo/src/pkg/domain.py",
            "package_init_path": "/repo/src/pkg/domain/__init__.py",
            "namespace": ["pkg", "domain"],
        }
    ]
    assert [item.kind for item in facts.nodes] == ["module", "package"]


def test_python_reasoning_tree_nodes_carry_agent_navigation_facts() -> None:
    facts = python_reasoning_tree_facts(
        (
            parse_python_source(
                '"""Domain package."""\n', path="/repo/src/pkg/domain/__init__.py"
            ),
            parse_python_source(
                '"""Service leaf."""\n\n\ndef build() -> None:\n    return None\n',
                path="/repo/src/pkg/domain/service.py",
            ),
        ),
        import_roots=("/repo/src",),
        project_root="/repo",
    )

    assert [item.to_dict() for item in facts.nodes] == [
        {
            "path": "/repo/src/pkg/domain/__init__.py",
            "namespace": ["pkg", "domain"],
            "kind": "package",
            "parent_namespace": ["pkg"],
            "child_names": ["service"],
            "has_intent_doc": True,
            "has_public_surface": False,
            "public_names": [],
            "export_contract_kind": "inferred",
            "is_valid": True,
            "effective_code_lines": 1,
        },
        {
            "path": "/repo/src/pkg/domain/service.py",
            "namespace": ["pkg", "domain", "service"],
            "kind": "module",
            "parent_namespace": ["pkg", "domain"],
            "child_names": [],
            "has_intent_doc": True,
            "has_public_surface": True,
            "public_names": ["build"],
            "export_contract_kind": "inferred",
            "is_valid": True,
            "effective_code_lines": 3,
        },
    ]


def test_python_reasoning_tree_nodes_expose_public_export_surface() -> None:
    facts = python_reasoning_tree_facts(
        (
            parse_python_source(
                '"""Facade."""\n\nfrom .service import build\n\n__all__ = ("build",)\n',
                path="/repo/src/pkg/domain/__init__.py",
            ),
            parse_python_source(
                '"""Service leaf."""\n\nVALUE = 1\n_private = 2\n\n\ndef build() -> None:\n    return None\n',
                path="/repo/src/pkg/domain/service.py",
            ),
        ),
        import_roots=("/repo/src",),
        project_root="/repo",
    )

    assert [
        (
            node.namespace,
            node.public_names,
            node.export_contract_kind,
            node.has_public_surface,
        )
        for node in facts.nodes
    ] == [
        (("pkg", "domain"), ("build",), "static", True),
        (("pkg", "domain", "service"), ("VALUE", "build"), "inferred", True),
    ]


def test_python_reasoning_tree_resolves_internal_import_edges() -> None:
    facts = python_reasoning_tree_facts(
        (
            parse_python_source(
                '"""Domain package."""\n',
                path="/repo/src/pkg/domain/__init__.py",
            ),
            parse_python_source(
                '"""Service leaf."""\n\n\ndef build() -> None:\n    return None\n',
                path="/repo/src/pkg/domain/service.py",
            ),
            parse_python_source(
                '"""Model leaf."""\n\nfrom .service import build as build_service\n',
                path="/repo/src/pkg/domain/models.py",
            ),
            parse_python_source(
                '"""Runner leaf."""\n\nimport pkg.domain.models as model_api\n',
                path="/repo/src/pkg/runner.py",
            ),
        ),
        import_roots=("/repo/src",),
        project_root="/repo",
    )

    assert [item.to_dict() for item in facts.import_edges] == [
        {
            "importer_path": "/repo/src/pkg/domain/models.py",
            "importer_namespace": ["pkg", "domain", "models"],
            "imported_path": "/repo/src/pkg/domain/service.py",
            "imported_namespace": ["pkg", "domain", "service"],
            "import_name": "build",
            "bound_name": "build_service",
            "scope": "",
            "line": 3,
            "column": 0,
            "is_relative": True,
        },
        {
            "importer_path": "/repo/src/pkg/runner.py",
            "importer_namespace": ["pkg", "runner"],
            "imported_path": "/repo/src/pkg/domain/models.py",
            "imported_namespace": ["pkg", "domain", "models"],
            "import_name": "pkg.domain.models",
            "bound_name": "model_api",
            "scope": "",
            "line": 3,
            "column": 0,
            "is_relative": False,
        },
    ]


def test_python_reasoning_tree_collects_branch_package_intent() -> None:
    facts = python_reasoning_tree_facts(
        (
            parse_python_source("", path="/repo/src/pkg/domain/__init__.py"),
            parse_python_source(
                '"""Service leaf."""\n', path="/repo/src/pkg/domain/service.py"
            ),
            parse_python_source(
                '"""Model leaf."""\n', path="/repo/src/pkg/domain/models.py"
            ),
        ),
        import_roots=("/repo/src",),
        project_root="/repo",
    )

    assert [item.to_dict() for item in facts.branches] == [
        {
            "path": "/repo/src/pkg/domain/__init__.py",
            "namespace": ["pkg", "domain"],
            "child_count": 2,
            "child_names": ["models", "service"],
            "has_intent_doc": False,
            "has_public_surface": False,
        }
    ]


def test_python_reasoning_tree_marks_documented_branch_package() -> None:
    facts = python_reasoning_tree_facts(
        (
            parse_python_source(
                '"""Domain package owner."""\n',
                path="/repo/src/pkg/domain/__init__.py",
            ),
            parse_python_source(
                '"""Service leaf."""\n', path="/repo/src/pkg/domain/service.py"
            ),
            parse_python_source(
                '"""Model leaf."""\n', path="/repo/src/pkg/domain/models.py"
            ),
        ),
        import_roots=("/repo/src",),
        project_root="/repo",
    )

    assert facts.branches[0].has_intent_doc is True
