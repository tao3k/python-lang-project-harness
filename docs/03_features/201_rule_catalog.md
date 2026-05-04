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
- `PY-PROJ-R005`: `[project]` metadata should declare package name.
- `PY-PROJ-R006`: `[project]` metadata should declare supported Python
  versions.
- `PY-PROJ-R007`: `[build-system]` tables should declare build requirements.
- `PY-PROJ-R008`: `[project].import-names` and `import-namespaces` should
  resolve to parser-visible project module owners.
- `PY-PROJ-R009`: console script, GUI script, and entry point targets should
  resolve to parser-visible project modules.
- `PY-PROJ-R010`: projects that declare the harness as a test/dev dependency
  should mount a parser-visible pytest gate.
- `PY-MOD-R001`: wildcard imports must become explicit imports.
- `PY-MOD-R002`: library modules should not use bare `print`.
- `PY-MOD-R003`: package facades with re-exports should declare `__all__`.
- `PY-MOD-R004`: library modules should not contain `breakpoint()`.
- `PY-MOD-R006`: large multi-responsibility modules should split behind a
  focused package facade.
- `PY-MOD-R007`: one Python import namespace should have one source owner,
  avoiding `module.py` plus `module/__init__.py` reasoning-tree shadows.
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
- `PY-AGENT-R007`: branch packages with multiple child modules should include
  a reasoning-tree intent docstring.

## Reasoning Tree Policy

The harness treats a Python project as an agent reasoning tree: import roots
lead to package branches, package branches lead to modules, and modules expose
the parser-owned public surface. `python_lang_parser` owns the tree facts:
tree nodes, child names, public/internal surface flags, module/package owner
shadows, internal import edges, and branch package child counts are derived
from `PythonModuleReport` paths, parser import records, module shape,
public-surface helpers, export candidates, `__all__` contract kind, module
docstrings, and parser-owned `pyproject.toml` metadata.

`PY-MOD-R007` blocks a collapsed owner tree such as `domain.py` next to
`domain/__init__.py`, because both spell the same import owner and repair
agents cannot know which surface owns the change. `PY-AGENT-R007` stays
advisory and asks branch package `__init__.py` files with multiple child
modules to carry a short intent docstring, so agents can choose the right
subtree before editing.

`render_python_reasoning_tree()` exposes the same tree as compact text for LLM
repair loops. It includes an `[imports]` section for parser-resolved
project-internal edges, a compact `[project]` section for declared package
metadata and entry targets, and compact `exports=` flags on public nodes,
making it the preferred first read when an agent needs to understand where a
change belongs, what public API it touches, and what it may affect before
touching code. In project-scoped reports, paths render relative to the project
root so the tree does not repeat long absolute prefixes.

## Rendered Diagnostic Policy

Rendered findings intentionally avoid large JSON payloads. The primary repair
surface is compact text:

1. stable rule id
2. source location
3. highlighted source line when available
4. short pointer label
5. one precise `Required:` contract line

Non-clean compact output is finding-first: it does not prepend a file-count or
issue-count header before the first blocking finding. Advice-only output starts
with `[advice]` and then concrete findings; it does not prepend an `[ok]`
summary or issue-count line. Clean output keeps only a short `[ok]` line plus
the file/parsed count needed for CI confidence. In project-scoped reports,
compact text renders paths relative to the project root; JSON keeps the
structured original paths for tooling.

`render_python_lang_harness()` includes advice by default. A report with only
`Info` findings is still clean, but its advice remains visible without
run-summary noise. Use
`render_python_lang_harness_advice()` when a caller wants only non-blocking
repair hints; it returns an empty string when there is no advice to act on.

Structured consumers should use `render_python_lang_harness_json()` or the
`PythonHarnessReport.to_dict()` shape instead of parsing compact text.

## Parser-First Policy

Python semantic policy is parser-first. Rule packs consume
`PythonModuleReport` facts instead of opening Python files and guessing from raw
text. `python_lang_parser` owns AST, compile, tokenize, symbol-table, source
line, module-shape, public-name, public-surface, symbol-role, and import-root
module identity facts, standard `pyproject.toml` project metadata, and package
reasoning-tree facts.
`python_lang_project_harness` owns rule catalogs, project/test layout,
reporting, and assertion behavior.

Repository tests enforce this boundary by rejecting direct `ast` or `tokenize`
usage under `src/python_lang_project_harness`. File and metadata checks may
still read non-Python policy inputs such as
`python-project-harness-rules.toml`; Python project metadata should flow
through parser-owned `pyproject.toml` facts.

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
