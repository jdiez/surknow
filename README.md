# cookie-claude

A comprehensive [cookiecutter](https://github.com/cookiecutter/cookiecutter) template for modern Python packages with first-class [Claude Code](https://claude.ai/claude-code) support.

Based on [osprey-oss/cookiecutter-uv](https://github.com/osprey-oss/cookiecutter-uv), enhanced with AI-assisted development tooling, strict type checking, and spec-driven workflows.

## Quickstart

```bash
# Interactive (prompts for each option)
uvx cookiecutter https://github.com/jdiez/cookie-claude.git

# Non-interactive (all defaults)
uvx cookiecutter https://github.com/jdiez/cookie-claude.git --no-input

# With custom values
uvx cookiecutter https://github.com/jdiez/cookie-claude.git \
  --no-input \
  author="Your Name" \
  email="you@example.com" \
  author_github_handle="yourhandle" \
  project_name="my-package"
```

## What you get

### Python toolchain

| Tool | Purpose |
|------|---------|
| [uv](https://docs.astral.sh/uv/) | Package management, virtual environments, lockfile |
| [hatchling](https://hatch.pypa.io/) | Build backend (src or flat layout) |
| [ruff](https://docs.astral.sh/ruff/) | Linting + formatting (20+ rule groups, Google docstring convention) |
| [mypy](https://mypy-lang.org/) | Strict type checking with pydantic plugin |
| [pytest](https://docs.pytest.org/) | Testing with doctests enabled |
| [deptry](https://deptry.com/) | Dependency auditing |
| [structlog](https://www.structlog.org/) | Structured logging |
| [pydantic](https://docs.pydantic.dev/) | Data validation (frozen models) |
| [pre-commit](https://pre-commit.com/) | Git hooks (ruff, debug-statements, detect-private-key) |
| [tox-uv](https://github.com/tox-dev/tox-uv) | Multi-version testing (Python 3.10-3.14) |
| [MkDocs](https://www.mkdocs.org/) | Documentation with Material theme (optional) |

### Claude Code integration

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Full Python dev guidance — uv conventions, toolchain, code style, structlog, Google docstrings |
| `.claude/settings.json` | Auto-allow uv/make/git commands, deny pip/conda, auto-format on file write |
| `.claude/commands/check` | Run full quality suite and fix issues |
| `.claude/commands/test` | Run tests with verbose output |
| `.claude/commands/implement` | Spec-driven TDD — decompose, write tests first, implement, verify |
| `.claude/commands/refactor` | Analyze module for smells, refactor with test guardrails |
| `.claude/commands/review-pr` | Review branch changes against project conventions |
| `.claude/commands/add-module` | Scaffold new module with logger, types, docstrings, and tests |

### CI/CD and GitHub

- **GitHub Actions** — quality checks + test matrix (3.10-3.14) on push/PR
- **Release workflow** — PyPI publish + docs deploy on GitHub release
- **Dependabot** — weekly dependency and Actions updates
- **PR template** — standardized checklist (types, docstrings, tests)
- **Issue templates** — bug reports and feature requests
- **SECURITY.md** — vulnerability reporting policy
- **CONTRIBUTING.md** — contribution guide with full workflow

### Conditional features

All toggleable during project creation:

- GitHub Actions CI/CD
- PyPI publishing
- MkDocs documentation
- Dockerfile
- Codecov coverage
- VS Code devcontainer
- License (MIT, BSD, ISC, Apache 2.0, GPL v3, or none)
- Dependency auditing (deptry)
- Layout (src or flat)

## Template variables

| Variable | Default | Description |
|----------|---------|-------------|
| `author` | `Your Name` | Author name |
| `email` | `you@example.com` | Author email |
| `author_github_handle` | `your-github-handle` | GitHub username |
| `project_name` | `my-python-project` | Project name (used for repo, package name) |
| `project_slug` | auto-generated | Python import name (derived from project_name) |
| `project_description` | `A Python package.` | One-line description |
| `layout` | `src` | `src` or `flat` |
| `include_github_actions` | `y` | Include CI/CD workflows |
| `publish_to_pypi` | `y` | Include PyPI release workflow |
| `deptry` | `y` | Include dependency auditing |
| `docs_tool` | `mkdocs` | `mkdocs` or `none` |
| `codecov` | `y` | Include code coverage |
| `dockerfile` | `y` | Include Dockerfile |
| `devcontainer` | `y` | Include VS Code devcontainer |
| `open_source_license` | `MIT license` | License type |

## After generation

The post-generation hook automatically runs `git init`, `uv sync`, and `pre-commit install`. Then:

```bash
cd your-project
make check    # verify everything passes
make test     # run tests
```

## License

MIT
