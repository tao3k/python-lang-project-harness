from __future__ import annotations

from python_lang_project_harness import (
    PythonProjectPolicyRulePack,
    python_project_policy_rules,
)


def test_project_policy_rule_pack_descriptor_and_catalog_are_stable() -> None:
    descriptor = PythonProjectPolicyRulePack().descriptor()
    rules = python_project_policy_rules()

    assert descriptor.id == "python.project_policy"
    assert descriptor.to_dict()["domains"] == [
        "project-policy",
        "packaging",
        "python",
    ]
    assert [rule.rule_id for rule in rules] == [
        "PY-PROJ-R001",
        "PY-PROJ-R002",
        "PY-PROJ-R003",
        "PY-PROJ-R004",
        "PY-PROJ-R005",
        "PY-PROJ-R006",
        "PY-PROJ-R007",
        "PY-PROJ-R008",
        "PY-PROJ-R009",
        "PY-PROJ-R010",
    ]
