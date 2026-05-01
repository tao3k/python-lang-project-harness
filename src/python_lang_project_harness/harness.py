"""Public facade for the embedded Python language project harness."""

from __future__ import annotations

from ._agent_policy import PythonAgentPolicyRulePack
from ._agent_policy_catalog import python_agent_policy_rules
from ._cli import run_cli, run_cli_from_env
from ._discovery import (
    discover_python_files,
    python_project_harness_paths,
    python_project_harness_scope,
)
from ._model import (
    PythonHarnessConfig,
    PythonHarnessFinding,
    PythonHarnessReport,
    PythonHarnessRule,
    PythonLangRulePack,
    PythonProjectHarnessScope,
    PythonRulePackDescriptor,
)
from ._modern_design import PythonModernDesignRulePack
from ._modern_design_catalog import python_modern_design_rules
from ._modularity import PythonModularityRulePack, python_modularity_rules
from ._project_policy import PythonProjectPolicyRulePack
from ._project_policy_catalog import python_project_policy_rules
from ._pytest import python_project_harness_test
from ._render import (
    render_python_lang_harness,
    render_python_lang_harness_advice,
    render_python_lang_harness_json,
)
from ._rule_packs import (
    default_python_harness_config,
    default_python_lang_rule_packs,
    python_rule_pack_descriptors,
)
from ._runner import (
    assert_python_lang_harness_clean,
    assert_python_project_harness_clean,
    run_python_lang_harness,
    run_python_project_harness,
)
from ._syntax import PythonSyntaxRulePack
from ._syntax_catalog import python_syntax_rules
from ._test_layout import PythonTestLayoutRulePack
from ._test_layout_catalog import python_test_layout_rules

__all__ = [
    "PythonAgentPolicyRulePack",
    "PythonHarnessConfig",
    "PythonHarnessFinding",
    "PythonHarnessReport",
    "PythonHarnessRule",
    "PythonLangRulePack",
    "PythonModernDesignRulePack",
    "PythonModularityRulePack",
    "PythonProjectHarnessScope",
    "PythonProjectPolicyRulePack",
    "PythonRulePackDescriptor",
    "PythonSyntaxRulePack",
    "PythonTestLayoutRulePack",
    "assert_python_lang_harness_clean",
    "assert_python_project_harness_clean",
    "default_python_harness_config",
    "default_python_lang_rule_packs",
    "discover_python_files",
    "python_agent_policy_rules",
    "python_modern_design_rules",
    "python_modularity_rules",
    "python_project_harness_paths",
    "python_project_harness_scope",
    "python_project_harness_test",
    "python_project_policy_rules",
    "python_rule_pack_descriptors",
    "python_syntax_rules",
    "python_test_layout_rules",
    "render_python_lang_harness",
    "render_python_lang_harness_advice",
    "render_python_lang_harness_json",
    "run_cli",
    "run_cli_from_env",
    "run_python_lang_harness",
    "run_python_project_harness",
]
