# Rule Catalog

:PROPERTIES:
:ID: 4af1b8e663ad854b94d6bd438596ab03c9829653
:TYPE: FEATURE
:STATUS: ACTIVE
:LAST_SYNC: 2026-04-30
:END:

The harness exposes deterministic rule metadata through compact library
functions:

- `python_rule_pack_descriptors()`
- `python_syntax_rules()`
- `python_modern_design_rules()`
- `python_project_policy_rules()`
- `python_agent_policy_rules()`
- `python_modularity_rules()`
- `python_test_layout_rules()`

## Default Rule Packs

Default project execution runs these packs:

1. `python.syntax`
2. `python.project_policy`
3. `python.modern_design`
4. `python.modularity`
5. `python.test_layout`
6. `python.agent_policy`

`python.agent_policy` is advisory by default and runs after the blocking packs.
The other default packs are blocking through `Warning` or `Error` findings.

## Blocking Rules

- `python.syntax.invalid`: Python source must parse through CPython-native
  syntax.
- `python.compile.invalid`: Python source must compile through CPython-native
  validation.
- `PY-PROJ-R001`: Python projects should use `src/` layout.
- `PY-PROJ-R002`: declared wheel package roots must be importable packages.
- `PY-PROJ-R003`: public typed package roots should include `py.typed`.
- `PY-PROJ-R004`: public callable boundaries in typed packages need
  annotations.
- `PY-MOD-R001`: wildcard imports must become explicit imports.
- `PY-MOD-R002`: library modules should not use bare `print`.
- `PY-MOD-R003`: package facades with re-exports should declare `__all__`.
- `PY-MOD-R004`: library modules should not contain `breakpoint()`.
- `PY-MOD-R006`: large multi-responsibility modules should split behind a
  focused package facade.
- `PY-TEST-R001`: pytest modules should not be scattered in the tests root.
- `PY-TEST-R002`: tests root entries should be owned suite directories or
  harness configuration files.
- `PY-TEST-R003`: large unit-test leaves should split into folder-first suites.

Project-local pytest-layout exceptions live in
`tests/python-project-harness-rules.toml`; each exception needs a non-empty
explanation before it suppresses `PY-TEST-*` findings.

## Agent Advice Rules

`PY-AGENT-*` rules are `Info` findings. They are designed as repair hints for
LLMs and are not blocking by default.

- `PY-AGENT-R001`: public module surface lacks an intent docstring.
- `PY-AGENT-R002`: public callable lacks type annotations.
- `PY-AGENT-R003`: public callable name conflicts across namespaces.
- `PY-AGENT-R004`: module namespace repeats a path segment.
- `PY-AGENT-R005`: public type name conflicts across namespaces.
- `PY-AGENT-R006`: public value name conflicts across namespaces.

## Rendered Diagnostic Policy

Rendered findings intentionally avoid large JSON payloads. The primary repair
surface is compact text:

1. stable rule id
2. source location
3. highlighted source line when available
4. short pointer label
5. one precise `Required:` contract line

`render_python_lang_harness()` includes advice by default. A report with only
`Info` findings is still clean, but its advice remains visible. Use
`render_python_lang_harness_advice()` when a caller wants only non-blocking
repair hints.

Structured consumers should use `render_python_lang_harness_json()` or the
`PythonHarnessReport.to_dict()` shape instead of parsing compact text.

## Parser-First Policy

Python semantic policy is parser-first. Rule packs consume
`PythonModuleReport` facts instead of opening Python files and guessing from raw
text. `python_lang_parser` owns AST, compile, tokenize, symbol-table, source
line, module-shape, public-name, public-surface, symbol-role, and import-root
module identity facts.
`python_lang_project_harness` owns rule catalogs, project/test layout,
reporting, and assertion behavior.

Repository tests enforce this boundary by rejecting direct `ast` or `tokenize`
usage under `src/python_lang_project_harness`. File and metadata checks may
still read non-Python policy inputs such as `pyproject.toml` and
`python-project-harness-rules.toml`.

## Snapshot Coverage

The compact text and JSON render contracts are covered by repository snapshots
under `tests/unit/snapshots`:

- `python_project_harness_compact_text.snap`
- `python_project_harness_json.snap`

Policy snapshots are generated from real harness fixtures and normalized to
`$TEMP` paths. Every current `PY-AGENT-*` rule has a compact advice snapshot.
The blocking policy surface also has snapshots for native syntax,
`PY-MOD-*`, `PY-PROJ-*`, and `PY-TEST-*` findings. This keeps rule titles,
pointer labels, source snippets, and `Required:` contracts reviewable as
ordinary snapshot diffs.

Refresh snapshots explicitly:

```shell
PYTHON_HARNESS_UPDATE_SNAPSHOTS=1 direnv exec . uv run --group test pytest \
  tests/unit/harness/test_render_snapshots.py \
  tests/unit/harness/test_agent_policy_snapshots.py \
  tests/unit/harness/test_policy_snapshots.py -q
```

:RELATIONS:
:LINKS: [Harness Boundary](../01_core/101_harness_boundary.md)
:END:
