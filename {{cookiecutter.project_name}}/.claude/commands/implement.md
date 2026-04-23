Implement a feature or fix using spec-driven TDD. Argument: $ARGUMENTS (spec/issue description)

Follow this workflow strictly:

1. **Decompose** the spec into discrete, testable requirements
2. **Write tests first** in `tests/` for each requirement — tests MUST fail initially
3. **Implement** the minimum code to make each test pass, one at a time
4. **Verify types**: Run `uv run mypy` after each module change
5. **Verify lint**: Run `uv run ruff check --fix` and `uv run ruff format`
6. **Run full suite**: `uv run python -m pytest tests -v` — all tests must pass
7. **Review**: Check that all new code follows project conventions:
   - Type annotations on all public functions
   - Google-style docstrings on all public functions/classes
   - structlog logger if the module does any logging
   - Pydantic models use `frozen=True`
   - No `list` where `tuple` should be used for immutable collections

Report a summary of what was implemented, tests added, and any design decisions made.
