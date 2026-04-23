{% raw %}# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.
{% endraw %}
## What This Is

**{{cookiecutter.project_name}}** — {{cookiecutter.project_description}}

## uv Environment — PIVOTAL

**uv is the sole package manager and environment tool.** All development commands MUST go through uv. Never use pip, pip-tools, poetry, or conda.

{% raw %}```bash
# Environment setup (do this first, always)
uv sync                  # Install all dependencies into .venv
uv run <command>         # Run ANY command inside the uv-managed venv

# NEVER do this:
# pip install ...        # WRONG — bypasses uv lockfile
# python -m pytest       # WRONG — may use wrong Python
# mypy src/              # WRONG — may use wrong mypy version

# ALWAYS do this:
uv run python -m pytest  # Correct
uv run mypy              # Correct
uv run ruff check .      # Correct
```{% endraw %}

When adding dependencies:
{% raw %}```bash
uv add pydantic                    # Add runtime dependency
uv add --group dev pytest          # Add dev dependency
```{% endraw %}

The `uv.lock` file is the source of truth for reproducible builds. Never edit it manually.

{% if cookiecutter.layout == "src" -%}
## Project Structure

{% raw %}```{% endraw %}
{{cookiecutter.project_name}}/
├── pyproject.toml
├── uv.lock
├── Makefile
├── src/
│   └── {{cookiecutter.project_slug}}/
│       ├── __init__.py
│       └── ...
├── tests/
│   └── test_*.py
{%- if cookiecutter.docs_tool == "mkdocs" %}
├── docs/
│   ├── index.md
│   └── modules.md
├── mkdocs.yml
{%- endif %}
{%- if cookiecutter.include_github_actions == "y" %}
├── .github/workflows/
{%- endif %}
├── .pre-commit-config.yaml
└── CLAUDE.md
{% raw %}```{% endraw %}
{%- else -%}
## Project Structure

{% raw %}```{% endraw %}
{{cookiecutter.project_name}}/
├── pyproject.toml
├── uv.lock
├── Makefile
├── {{cookiecutter.project_slug}}/
│   ├── __init__.py
│   └── ...
├── tests/
│   └── test_*.py
{%- if cookiecutter.docs_tool == "mkdocs" %}
├── docs/
│   ├── index.md
│   └── modules.md
├── mkdocs.yml
{%- endif %}
{%- if cookiecutter.include_github_actions == "y" %}
├── .github/workflows/
{%- endif %}
├── .pre-commit-config.yaml
└── CLAUDE.md
{% raw %}```{% endraw %}
{%- endif %}

## Development Commands

All commands use uv under the hood:

{% raw %}```bash
make install     # uv sync + pre-commit install
make check       # Lock consistency, pre-commit, mypy, deptry
make test        # uv run pytest with doctests
make build       # Build wheel via uv
```{% endraw %}
{%- if cookiecutter.docs_tool == "mkdocs" %}
{% raw %}```bash
make docs        # Serve docs locally
make docs-test   # Verify docs build cleanly
```{% endraw %}
{%- endif %}

## Toolchain

- **Package manager:** uv (sole environment and dependency tool)
- **Build backend:** hatchling ({% if cookiecutter.layout == "src" %}src{% else %}flat{% endif %} layout)
- **Validation/modeling:** pydantic v2 (frozen models, mypy plugin)
- **Logging:** structlog (structured events, stdlib integration, library-safe)
- **Linting/formatting:** ruff (line-length 120, Google docstring convention)
- **Type checking:** mypy (strict mode + pydantic plugin)
{%- if cookiecutter.deptry == "y" %}
- **Dependency auditing:** deptry
{%- endif %}
- **Testing:** pytest (doctests enabled)
{%- if cookiecutter.docs_tool == "mkdocs" %}
- **Docs:** MkDocs + Material theme + mkdocstrings
{%- endif %}
- **Pre-commit:** ruff, pre-commit-hooks (debug-statements, detect-private-key)
{%- if cookiecutter.include_github_actions == "y" %}
- **CI:** GitHub Actions on PR and merge to main
{%- endif %}
- **Multi-version testing:** tox-uv (Python 3.10-3.14)

## Code Conventions

- Python >=3.10, <4.0
- All public functions must have type annotations (mypy strict mode)
- All models use pydantic `BaseModel` with `frozen=True` (immutable by default)
- Collection fields use `tuple[X, ...]` not `list[X, ...]` (hashable, immutable)
- Enums use `(str, Enum)` mixin for JSON serialization
- Tests go in `tests/` mirroring source structure
- Test files may use `assert` (S101 suppressed in `tests/`)

## Design Principles

### Choose the right paradigm for the problem

- **OOP when modeling entities with state and behavior** — domain objects, services with lifecycle, anything where identity and encapsulation matter. Use classes, inheritance (prefer composition), and protocols.
- **Functional when transforming data** — pure functions for pipelines, data processing, validation logic, anything stateless. Prefer `map`/`filter`/`reduce`, comprehensions, and `functools` over mutable loops.
- **Don't force one paradigm everywhere.** A module can mix both. A class can have functional helper functions. A data pipeline doesn't need a class wrapper.

### Design patterns — use when they solve a real problem

- **Apply patterns to solve actual complexity**, not to add structure for its own sake. A Strategy pattern is warranted when you have 3+ interchangeable algorithms; a single `if/else` doesn't need it.
- **Prefer simple over clever.** A function is better than a class with one method. A dict is better than a Factory when you have a static mapping. Protocols are better than deep inheritance hierarchies.
- **Common patterns that fit Python well:** Strategy (callables/protocols), Factory (classmethods), Observer (callbacks/signals), Builder (fluent APIs / dataclass construction), Repository (data access abstraction).
- **Patterns to avoid unless truly needed:** Singleton (use module-level instances), Abstract Factory (over-engineering in Python), Visitor (use `match`/`functools.singledispatch` instead).

### Async and concurrency — match the workload

- **Use `async`/`await` for I/O-bound concurrency** — network calls, database queries, file I/O, external APIs. Don't make things async "just in case."
- **Use `multiprocessing` / `concurrent.futures.ProcessPoolExecutor` for CPU-bound parallelism** — heavy computation, data crunching, image processing. The GIL makes threading useless here.
- **Use `threading` / `concurrent.futures.ThreadPoolExecutor` for I/O-bound parallelism in sync code** — when async isn't feasible (legacy code, sync libraries).
- **Default to sync.** Only introduce async or multiprocessing when there's a measurable performance need or the workload naturally demands it. Premature concurrency adds complexity without benefit.
- **Never mix paradigms carelessly.** Don't call sync blocking code inside async functions without `asyncio.to_thread()`. Don't share mutable state across processes without explicit synchronization.

### Error handling

- **Fail fast and explicitly.** Raise specific exceptions at the point of failure. Don't swallow errors or return `None` to signal failure.
- **Custom exceptions for domain errors.** Use a project exception hierarchy rooted in a base class. Catch specific exceptions, not bare `except`.
- **Validate at boundaries, trust internally.** Validate user input, API responses, and external data. Internal function calls between trusted modules don't need redundant validation.

## Logging Convention — structlog

**This project uses structlog for structured logging.** If this is a library, never configure structlog output — only bind context and emit events. App consumers own configuration.

### Logger Creation

One module-level logger per file:

{% raw %}```python
import structlog

logger: structlog.stdlib.BoundLogger = structlog.get_logger("{% endraw %}{{cookiecutter.project_slug}}{% raw %}.module_name")
```{% endraw %}

### Event Naming

Dot-separated, lowercase, past tense:

{% raw %}```python
logger.info("resource.created", resource_id=resource.id)
logger.warning("operation.retried", attempt=3)
logger.error("validation.failed", errors=errors)
logger.debug("cache.hit", key=cache_key)
```{% endraw %}

### Context Binding

{% raw %}```python
log = logger.bind(request_id=request_id, user_id=user_id)
log.info("request.started")
# ...bound context carries through
log.info("request.completed", duration_ms=elapsed)
```{% endraw %}

### Log Levels

| Level | When |
|-------|------|
| `debug` | Internal state changes, cache operations, detailed flow |
| `info` | Significant lifecycle events, operations started/completed |
| `warning` | Recoverable issues, retries, deprecations |
| `error` | Failures, invalid state, unrecoverable errors |

## Docstring Convention — Google Style

**All** packages, modules, classes, methods, and functions must have Google-style docstrings:

{% raw %}```python
"""Module-level docstring — one-line summary.

Extended description of the module's purpose and contents.
"""


class MyClass:
    """One-line summary of the class.

    Attributes:
        name: Description of the attribute.
        value: Description of the attribute.
    """


def my_function(arg: str) -> bool:
    """One-line summary of the function.

    Extended description if needed.

    Args:
        arg: Description of the argument.

    Returns:
        Description of the return value.

    Raises:
        ValueError: Description of when this is raised.
    """
```{% endraw %}
{%- if cookiecutter.docs_tool == "mkdocs" %}

mkdocstrings is configured to parse Google-style docstrings for auto-generated API docs.
{%- endif %}

## Release Discipline

Before every **commit**, the following should pass:

{% raw %}```bash
make check && make test
```{% endraw %}

{%- if cookiecutter.publish_to_pypi == "y" %}

For releases:
1. Update version in `pyproject.toml`
2. Create annotated git tag (`git tag -a vX.Y.Z -m "..."`)
3. Push with `--tags` to trigger the release workflow
{%- endif %}
