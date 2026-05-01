# Runner Modes

:PROPERTIES:
:ID: 6e7f9f6485d9445d80b469bb7ee67ad8c791a4a1
:TYPE: FEATURE
:STATUS: ACTIVE
:LAST_SYNC: 2026-04-30
:END:

The harness exposes two runner modes with shared configuration.

## Project Runner

Use `run_python_project_harness()` or `assert_python_project_harness_clean()`
when a caller has a project root. The project runner scans the whole Python
project root by default, attaches `PythonProjectHarnessScope`, and runs the
full default rule surface:

1. `python.syntax`
2. `python.project_policy`
3. `python.modern_design`
4. `python.modularity`
5. `python.test_layout`
6. `python.agent_policy`

The project root must exist. Missing roots raise `ValueError` in library calls
and produce CLI exit code `2`.

## Configuration

`PythonHarnessConfig` owns project-scope classification and parser inclusion:

```python
from python_lang_project_harness import PythonHarnessConfig

config = PythonHarnessConfig(
    include_tests=False,
    source_dir_names=("lib",),
    test_dir_names=("checks",),
    extra_path_names=("examples", "tools/check.py"),
)
```

Function parameters such as `source_dir_names=("src",)` are explicit
classification overrides for a single call. If they are omitted, the project
runner uses the config.

By default, every Python file under the project root is parser scope, except
ignored environment/cache/build directories. `source_dir_names` and
`test_dir_names` classify roots for project and pytest-layout policy; they do
not narrow parser coverage. `extra_path_names` can add an external project path
or a single Python file outside the root. Extra paths are relative to the
project root and are part of `PythonProjectHarnessScope.monitored_paths` when
they exist.

`include_tests=False` removes test roots from parser discovery, while keeping
tests-root layout policy active. Callers can skip expensive or broken test
parsing without hiding suite-shape drift.

Explained local pytest-layout exceptions can be declared in
`tests/python-project-harness-rules.toml`:

```toml
[tests]
allowed_root_files = [
  { name = "test_contract_gate.py", explanation = "root gate mounts external contract tests" },
]
allowed_directories = [
  { name = "contract", explanation = "contract suite is mounted by a root gate" },
]
```

Entries without a non-empty `explanation` are ignored, so the normal
`PY-TEST-*` findings remain visible.

`blocking_severities` keeps the assertion contract independent from rule
emission. The default blocks `Warning` and `Error`; `Info` findings remain
visible advice.

## Explicit-Path Runner

Use `run_python_lang_harness()` or `assert_python_lang_harness_clean()` for
explicit files or directories. Requested paths must exist. This runner does not
attach a project scope, so project-scope evaluators stay quiet. File-local rule
packs can still run when they only need parser facts.

The explicit-path runner is useful for editor integrations, focused parser
checks, and small repair loops where the caller already knows the files to
inspect.

:RELATIONS:
:LINKS: [Harness Boundary](../01_core/101_harness_boundary.md), [Rule Catalog](201_rule_catalog.md), [CLI](203_cli.md)
:END:
