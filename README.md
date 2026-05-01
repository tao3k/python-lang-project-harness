# python-lang-project-harness

`python-lang-project-harness` is a standalone Python project harness library for
modern Python packages. It ships two library boundaries in one repo:

- `python_lang_parser`: Python-native AST, compiler, tokenize, symbol-table,
  module-shape, public-surface, and symbol-role facts.
- `python_lang_project_harness`: project discovery, deterministic rule
  packs, compact rendered diagnostics, and pytest-friendly assertions.

The harness is library-first. Callers pass a project root or explicit paths,
then decide whether to assert, render compact text, or inspect the structured
report. Compact text is the default agent repair surface; JSON is available for
tooling through `render_python_lang_harness_json()`.

`python_lang_parser` is the semantic foundation. Harness policy consumes parser
reports instead of re-parsing Python source in the rule layer; project metadata
and tests-root layout stay in the harness.

## Quick Use

```python
from pathlib import Path

from python_lang_project_harness import (
    __version__,
    assert_python_project_harness_clean,
    render_python_lang_harness,
    render_python_reasoning_tree,
    run_python_project_harness,
)


def test_python_project_harness_policy() -> None:
    assert_python_project_harness_clean(Path("."))


report = run_python_project_harness(Path("."))
print(__version__)
print(render_python_lang_harness(report))
print(render_python_reasoning_tree(report))
```

The project runner scans the whole Python project root by default, excluding
tool/cache/build directories such as `.venv`, `__pycache__`, `build`, and
`dist`. Conventional source and test roots still classify project policy, but
they do not narrow parser coverage. The explicit path runner,
`run_python_lang_harness([...])`, is useful for focused parser and syntax
checks.
Use `PythonHarnessConfig` to change source-root classification, test-root
classification, extra external project paths, test inclusion, or blocking
severities without hardcoding project-specific policy into the library.
Project runners also read `[tool.python-lang-project-harness]` from
`pyproject.toml` when no explicit `PythonHarnessConfig` is passed, including
`disabled_rule_ids` and `blocking_rule_ids` for stable rule-id policy.
When `include_tests=False`, test files are not parsed, but tests-root layout
policy still runs. Explained local exceptions can live in
`tests/python-project-harness-rules.toml`.

For agent repair loops, `render_python_reasoning_tree(report)` emits a compact
package/module owner tree from parser-owned facts. It shows package branches,
public/internal leaves, compact export names, child names, internal import
edges, and owner shadows without forcing an LLM to consume the full JSON report
first.

The console script follows the same render contract:

```shell
python-project-harness .
python-project-harness --json .
python-project-harness --source-dir lib --extra-path tools --no-tests .
python -m python_lang_project_harness .
```

## Pytest Dev Dependency

Downstream projects can load the harness through their test/dev dependency
group:

```toml
[dependency-groups]
test = [
  "pytest>=8",
  "python-lang-project-harness[pytest]>=0.1.0",
]

[tool.pytest.ini_options]
addopts = ["--python-project-harness"]
```

The pytest plugin is exposed through the package `pytest11` entry point. It is
loaded by pytest when the dev dependency is installed, but it only runs the
harness when `--python-project-harness` is enabled. Projects that prefer an
explicit test file can use the public helper:

```python
from python_lang_project_harness.pytest import python_project_harness_test

test_python_project_harness_policy = python_project_harness_test()
```

## Rule Packs

Default project execution runs these packs in order:

1. `python.syntax`
2. `python.project_policy`
3. `python.modern_design`
4. `python.modularity`
5. `python.test_layout`
6. `python.agent_policy`

`Warning` and `Error` findings block assertions by default. `Info` findings,
including `PY-AGENT-*` advice, stay visible in compact diagnostics without
blocking unless a caller opts into stricter severities.

Detailed package material lives under [`docs/`](docs/index.md).

## CI

GitHub Actions runs the package contract on every pull request and on pushes to
the default branch: `uv sync --group test --locked`, ruff format/check, pytest,
self-harness, wheel/sdist build, and diff hygiene.
