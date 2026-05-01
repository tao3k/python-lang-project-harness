from __future__ import annotations

from python_lang_parser import python_name_is_public, python_scope_is_public


def test_python_public_name_helpers_are_parser_owned() -> None:
    assert python_name_is_public("Service")
    assert not python_name_is_public("_Service")
    assert not python_name_is_public("test_service")
    assert python_scope_is_public("Service.Builder")
    assert not python_scope_is_public("_Private.Builder")
