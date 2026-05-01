from __future__ import annotations

from python_lang_parser import (
    parse_python_source,
    python_module_has_public_surface,
    python_module_has_public_symbol_surface,
)


def test_python_module_public_surface_helpers_are_parser_owned() -> None:
    public_symbol_report = parse_python_source(
        """
def build():
    return None
""",
        path="service.py",
    )
    public_value_report = parse_python_source("VALUE = 1\n", path="settings.py")
    private_report = parse_python_source(
        """
def _hidden():
    return None
""",
        path="private.py",
    )

    assert python_module_has_public_symbol_surface(public_symbol_report)
    assert python_module_has_public_surface(public_symbol_report)
    assert not python_module_has_public_symbol_surface(public_value_report)
    assert python_module_has_public_surface(public_value_report)
    assert not python_module_has_public_symbol_surface(private_report)
    assert not python_module_has_public_surface(private_report)
