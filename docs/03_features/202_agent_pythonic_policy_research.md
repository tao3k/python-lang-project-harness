# Agent Pythonic Policy Research

This note records the evidence behind agent-facing Python readability policy.
The goal is not to replace formatters, linters, type checkers, or pytest. The
goal is to give repair agents a compact reasoning-tree contract for the parts
those tools do not own: algorithm shape, public edit boundaries, and native
Python idioms that keep code small enough for an LLM to edit reliably.

## Evidence

Official Python guidance gives the north star. PEP 20 names the shape values
directly: explicit code, simple code, flat control flow, sparse structure,
readability, one obvious way, and implementations that are easy to explain.
PEP 8 makes the operational point: code is read much more than written, and
project-local consistency matters more than blind rule application.

Modern Python also has native constructs that remove common LLM boilerplate:

- `match/case` is the language-level pattern matching construct for structured
  branching.
- list comprehensions are documented as the concise way to build mapped or
  filtered lists; the tutorial explicitly contrasts them with an empty list
  plus an append loop.
- `itertools` provides fast, memory efficient iterator building blocks that can
  be composed into compact pure-Python pipelines.
- built-ins such as `any`, `all`, `sum`, `next`, `sorted`, `zip`, `list`,
  `dict`, and `set` make common loop intents explicit.
- `collections.Counter` and `collections.defaultdict` are specialized
  containers for counting and grouping, so agents should not spell those
  algorithms as hand-managed dictionary state.
- `dataclasses` turn plain data carriers into annotated, generated-method data
  models instead of hand-written storage classes.
- `typing` is not runtime enforcement, but it gives tools and agents explicit
  callable and data shapes.

GitHub practice shows the adjacent tool baseline. Current mature Python repos
such as `pydantic/pydantic`, `pytest-dev/pytest`, `encode/httpx`, and
`psf/black` centralize project metadata in `pyproject.toml` and commonly wire
pytest, ruff, mypy, or pyright. That means this harness should not duplicate
style or type-check rules. Its useful scope is the parser-backed project and
algorithm contract that an LLM sees before it edits code.

## Harness Thesis

The harness should classify Python quality in three layers:

1. Tool substrate: packaging metadata, pytest gate, ruff, and type-checker
   configuration. Parser facts expose this layer, but normal tools enforce it.
2. Project reasoning tree: packages, public facades, owner maps, imports, and
   public callable/type/value boundaries. This is where an agent chooses where
   to edit.
3. Algorithm readability for agents: public functions should expose a small
   algorithm surface through guard clauses, native dispatch, comprehensions,
   iterator tools, built-ins, and named pipeline steps.

The third layer is where policy adds value. LLMs often spell Python as generic
pseudocode: nested `if`/`else`, broad loops, empty accumulator containers,
boolean flags, and manual search loops. Python has native idioms for many of
these shapes. A parser-backed advisory rule can point agents toward those
idioms without blocking valid explicit loops.

## Rule Direction

Existing rules cover two algorithm-shape problems:

- `PY-AGENT-R009`: nested control flow and literal dispatch ladders.
- `PY-AGENT-R010`: broad linear public functions.

The next policy step is not another size threshold. It is native-idiom advice:
when the parser sees a simple module-level function or public method manually
building a list, set, or dict in a loop, manually counting/grouping into a
dictionary, manually summing numeric values, or returning a boolean through a
trivial predicate loop, the harness should ask the agent to use a comprehension,
generator expression, built-in such as `sum`/`any`/`all`,
`collections.Counter`, `collections.defaultdict`, or named iterator pipeline.
This is advisory because explicit loops remain correct for side effects,
complex state machines, debugging, or performance-sensitive code that has been
measured.

## Candidate Matrix

| Candidate | Evidence | Harness action |
| --- | --- | --- |
| Map/filter/list/set/dict build loops | Python Functional HOWTO on comprehensions and generator expressions | Implemented by parser fact `manual_collection_loop_count` |
| Predicate search loops | Python built-ins and Functional HOWTO predicate guidance | Implemented by parser fact `manual_predicate_loop_count` |
| Dictionary counting/grouping loops | `collections.Counter` and `defaultdict` official docs; pytest and pydantic use both in project code | Implement as parser facts for manual counter/grouping loops |
| Numeric accumulation loops | Built-in `sum` and generator expression guidance | Implement as parser fact for simple `total += expr` loops |
| Data carrier classes | `dataclasses` official docs | Research-only for now; needs class-field parser facts before policy |
| Resource lifetime / context managers | `contextlib` and `pathlib` docs, plus existing Ruff coverage | Defer to tool substrate unless parser can prove unsafe lifetime |
| Type dispatch | `match/case` and `functools.singledispatch` docs | Covered partly by `PY-AGENT-R009`; enrich later only with concrete parser facts |

## Sources

- https://peps.python.org/pep-0020/
- https://peps.python.org/pep-0008/
- https://docs.python.org/3/reference/compound_stmts.html#the-match-statement
- https://docs.python.org/3/tutorial/datastructures.html#list-comprehensions
- https://docs.python.org/3/library/itertools.html
- https://docs.python.org/3/library/functions.html
- https://docs.python.org/3/library/dataclasses.html
- https://docs.python.org/3/library/typing.html
- https://packaging.python.org/en/latest/guides/writing-pyproject-toml/
- https://github.com/pydantic/pydantic
- https://github.com/pytest-dev/pytest
- https://github.com/encode/httpx
- https://github.com/psf/black
