from __future__ import annotations

from typing import TYPE_CHECKING

from python_lang_parser import parse_python_project_metadata

if TYPE_CHECKING:
    from pathlib import Path


def test_parse_python_project_metadata_collects_modern_project_facts(
    tmp_path: Path,
) -> None:
    package = tmp_path / "src" / "example_pkg"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        """
[project]
name = "example-pkg"
requires-python = ">=3.12"
import-names = ["example_pkg", "_example_private ; private"]
import-namespaces = ["example_namespace"]

[project.scripts]
example = "example_pkg.cli:main"

[project.entry-points.pytest11]
example_pkg = "example_pkg.pytest_plugin"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/example_pkg"]
""".lstrip(),
        encoding="utf-8",
    )

    metadata = parse_python_project_metadata(tmp_path)

    assert metadata is not None
    assert metadata.project_name == "example-pkg"
    assert metadata.requires_python == ">=3.12"
    assert metadata.build_backend == "hatchling.build"
    assert metadata.build_requires == ("hatchling",)
    assert metadata.wheel_packages == ("src/example_pkg",)
    assert metadata.package_roots == (package,)
    assert [item.to_dict() for item in metadata.import_names] == [
        {
            "name": "example_pkg",
            "namespace": ["example_pkg"],
            "is_private": False,
            "source_value": "example_pkg",
        },
        {
            "name": "_example_private",
            "namespace": ["_example_private"],
            "is_private": True,
            "source_value": "_example_private ; private",
        },
    ]
    assert [item.to_dict() for item in metadata.import_namespaces] == [
        {
            "name": "example_namespace",
            "namespace": ["example_namespace"],
            "is_private": False,
            "source_value": "example_namespace",
        }
    ]
    assert [item.to_dict() for item in metadata.scripts] == [
        {
            "name": "example",
            "target": "example_pkg.cli:main",
            "kind": "console",
        }
    ]
    assert [item.to_dict() for item in metadata.entry_points] == [
        {
            "group": "pytest11",
            "name": "example_pkg",
            "target": "example_pkg.pytest_plugin",
        }
    ]


def test_parse_python_project_metadata_derives_package_roots_from_import_names(
    tmp_path: Path,
) -> None:
    package = tmp_path / "src" / "example_pkg"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        """
[project]
name = "example-pkg"
requires-python = ">=3.12"
import-names = ["example_pkg"]
""".lstrip(),
        encoding="utf-8",
    )

    metadata = parse_python_project_metadata(tmp_path)

    assert metadata is not None
    assert metadata.wheel_packages == ()
    assert metadata.package_roots == (package,)
