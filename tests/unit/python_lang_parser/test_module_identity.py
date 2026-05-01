from __future__ import annotations

from python_lang_parser import (
    python_module_is_package_init,
    python_module_name_from_path,
    python_module_namespace_parts,
)


def test_python_module_identity_helpers_follow_import_roots() -> None:
    assert python_module_name_from_path("/repo/src/pkg/service.py") == "service"
    assert python_module_namespace_parts(
        "/repo/src/pkg/domain/domain/service.py",
        import_roots=("/repo/src",),
        project_root="/repo",
    ) == ("pkg", "domain", "domain", "service")
    assert python_module_namespace_parts(
        "/repo/src/pkg/__init__.py",
        import_roots=("/repo/src",),
    ) == ("pkg",)
    assert python_module_namespace_parts(
        "/repo/tools/check.py",
        import_roots=("/repo/tools/check.py",),
        project_root="/repo",
    ) == ("check",)
    assert python_module_is_package_init("/repo/src/pkg/__init__.py")
    assert not python_module_is_package_init("/repo/src/pkg/service.py")
