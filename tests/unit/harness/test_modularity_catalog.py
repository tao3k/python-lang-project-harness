from __future__ import annotations

from typing import TYPE_CHECKING

from python_lang_project_harness import run_python_project_harness

if TYPE_CHECKING:
    from pathlib import Path


def test_modularity_rule_pack_blocks_large_class_only_service_module(
    tmp_path: Path,
) -> None:
    src = tmp_path / "src"
    src.mkdir()
    source = src / "services.py"
    source.write_text(_large_class_only_service_module_source(), encoding="utf-8")

    report = run_python_project_harness(tmp_path)

    assert [
        (finding.rule_id, finding.location.path) for finding in report.findings
    ] == [
        ("PY-MOD-R006", str(source)),
    ]


def _large_class_only_service_module_source() -> str:
    parts = ['"""Large class-only service module for tests."""\n\n']
    for index in range(12):
        parts.append(
            f"class Service{index}:\n"
            "    def __init__(self, value: int) -> None:\n"
            "        self.value = value\n\n"
        )
        for method_index in range(6):
            parts.append(
                f"    def handle_{method_index}(self, input_value: int) -> int:\n"
            )
            for line in range(3):
                parts.append(f"        value_{line} = input_value + {line}\n")
            parts.append("        return value_0 + self.value\n\n")
    return "".join(parts)
