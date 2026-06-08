# python-lang-project-harness

## Harness Rules

Generated from embedded `src/python_lang_project_harness/harness-rules.md`.

- **PY-AGENT-R001**: Requires library modules to declare concise intent docstrings for agent search and repair.
- **PY-AGENT-R002**: Requires public callable boundaries to carry type annotations for native syntax reasoning.
- **PY-AGENT-R003**: Detects public callable name conflicts that make project-level intent ambiguous.
- **PY-AGENT-R004**: Detects repeated Python module path segments that obscure ownership paths.
- **PY-AGENT-R005**: Detects public type name conflicts that make project-level type intent ambiguous.
- **PY-AGENT-R006**: Detects public value name conflicts that make configuration or value intent ambiguous.
- **PY-AGENT-R007**: Requires branch packages to document reasoning-tree intent before agents choose an owner subtree.
- **PY-AGENT-R008**: Flags broad mixed branch packages that need focused subpackages or facade owner maps.
- **PY-AGENT-R009**: Requires nested Python algorithms to expose shape through guards, dispatch, matches, or named steps.
- **PY-AGENT-R010**: Splits broad public Python functions into named helpers or pipeline steps.
- **PY-AGENT-R011**: Replaces manual Python transforms with comprehensions, built-ins, counters, defaults, or named iterator helpers.
- **PY-AGENT-R012**: Requires public data-shaped classes to use visible dataclass, typed, protocol, enum, or model anchors.
- **PY-MOD-R001**: Replaces wildcard imports with explicit imported names.
- **PY-MOD-R002**: Replaces bare library prints with logging, return values, or explicit test assertions.
- **PY-MOD-R003**: Requires package facade re-exports to declare an explicit public export contract.
- **PY-MOD-R004**: Removes debugger breakpoints from library modules.
- **PY-MOD-R006**: Splits large multi-responsibility Python modules behind explicit package facades.
- **PY-MOD-R007**: Keeps one source owner for each Python import namespace branch.
- **PY-PROJ-R001**: Requires Python projects to use src layout for installed package import resolution.
- **PY-PROJ-R002**: Requires declared wheel package roots to be importable package directories.
- **PY-PROJ-R003**: Requires typed public packages to ship py typed markers.
- **PY-PROJ-R004**: Requires public callables in typed packages to carry annotations.
- **PY-PROJ-R005**: Requires project metadata to declare the package name.
- **PY-PROJ-R006**: Requires project metadata to declare supported Python versions.
- **PY-PROJ-R007**: Requires build-system tables to declare build requirements.
- **PY-PROJ-R008**: Requires declared import names to resolve to parser-visible project modules.
- **PY-PROJ-R009**: Requires entry point targets to resolve to parser-visible project modules.
- **PY-PROJ-R010**: Requires harness dev dependencies to mount an actual pytest gate.
- **PY-PROJ-R011**: Requires verification profile hints or agent snapshot guidance for parser-suggested owners.
- **PY-TEST-R001**: Moves pytest modules out of the tests root and into owned suites.
- **PY-TEST-R002**: Keeps tests root limited to harness configuration and owned suite directories.
- **PY-TEST-R003**: Splits oversized unit test leaves into focused folder-first suites.
