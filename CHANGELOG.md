# Changelog

All notable changes to this project will be documented in this file.

## [0.3.0] - 2026-05-12

### Added

- **Bandit security scanning**: `bandit[toml]>=1.8.0` dev dependency with pyproject.toml configuration
- **Pre-commit bandit hook**: runs on every commit with `-ll` (medium+ severity)
- **`make security` target**: standalone bandit scan command
- **CI security step**: bandit runs in GitHub Actions quality job
- **CLAUDE.md security section**: table of key bandit rules for AI-generated code (B105, B307, B301, B324, B608, B110, B506)
- **Claude Code hook**: PostToolUse runs bandit on `.py` files after edit/write, PreToolUse reminder includes security patterns
- **Permission**: `Bash(uv run bandit*)` auto-allowed in `.claude/settings.json`
- **Anti-pattern**: "Do not add `# nosec` without a specific rule code and justification" in What NOT to Do

## [0.2.0] - 2026-05-05

### Added

- **"How to Work in This Codebase" section**: AI behavioral guidelines (think-first, surgical changes, goal-driven execution) inspired by Karpathy's coding philosophy
- **"What NOT to Do" section**: 9 explicit anti-patterns as AI guardrails (no pip, no manual venvs, no bare type: ignore, etc.)
- **Expanded dependency commands**: `uv add --dev`, `uv remove`, `uv lock`, `uv lock --upgrade`, named dependency groups
- **`uvx` one-off tool execution**: guidance for running tools not in project dependencies
- **Version tracking header**: `<!-- Last verified against: uv 0.7.x, ruff 0.11.x, mypy 1.15.x, pytest 8.x -->`
- **No `__init__.py` in tests** note in Toolchain section

### Changed

- Dependency example uses `--dev` (PEP 735) instead of verbose `--group dev`

## [0.1.0] - 2026-04-23

### Added

- Initial cookiecutter template based on osprey-oss/cookiecutter-uv
- **Python toolchain**: uv, hatchling, ruff (20+ rule groups), mypy strict, pytest, deptry, structlog, pydantic
- **CLAUDE.md**: comprehensive Python dev guidance (uv conventions, toolchain, code style, structlog logging, Google docstrings)
- **`.claude/settings.json`**: auto-permissions (uv/make/git allowed, pip/conda denied), PostToolUse hook for auto ruff format on `.py` writes
- **`.claude/commands/`**: 6 slash commands — `/check`, `/test`, `/implement`, `/refactor`, `/review-pr`, `/add-module`
- **GitHub Actions CI**: quality checks + test matrix (Python 3.10-3.14)
- **Release workflow**: PyPI publish + MkDocs docs deploy on GitHub release
- **Dependabot**: weekly dependency and GitHub Actions updates
- **GitHub templates**: PR template, bug report, feature request
- **SECURITY.md**: vulnerability reporting policy
- **CONTRIBUTING.md**: full contribution workflow guide
- **Pre-commit hooks**: ruff check/format, debug-statements, detect-private-key, standard file checks
- **tox-uv**: multi-version Python testing
- **Conditional features**: GitHub Actions, PyPI, MkDocs, Dockerfile, codecov, devcontainer, deptry, 5 license variants
- **Post-generation hook**: automatic git init, uv sync, pre-commit install
- **`py.typed`**: PEP 561 marker for downstream type checking
- **`.python-version`**: pins Python 3.12 for tool compatibility
