Review the current branch's changes against project conventions. No arguments needed.

1. Run `git diff main...HEAD` (or `git diff HEAD~1` if on main) to see all changes
2. Check each changed `.py` file against project conventions:
   - **Type safety**: All public functions have full type annotations? mypy strict passes?
   - **Docstrings**: All public functions/classes have Google-style docstrings?
   - **Logging**: Uses structlog (not print/logging)? Event names follow `module.action_result` pattern?
   - **Models**: Pydantic models use `frozen=True`? Collections use `tuple` not `list`?
   - **Tests**: Every new function has a corresponding test? Test files use `assert` directly?
   - **Security**: No hardcoded secrets, credentials, or API keys? No SQL injection vectors?
   - **Dependencies**: Any new imports? Are they in pyproject.toml?
3. Run `make check` to verify lint/type/dep checks pass
4. Run `make test` to verify all tests pass
5. Report findings as: PASS (convention met) or FLAG (needs attention) for each check
