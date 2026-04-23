# Changelog

All notable changes to this project will be documented in this file.

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
