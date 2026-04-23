Analyze and refactor a module with test guardrails. Argument: $ARGUMENTS (module path or name)

1. **Read** the target module and its existing tests
2. **Run baseline tests**: `uv run python -m pytest tests -v` — record current pass count
3. **Analyze** for code smells:
   - Duplicated logic that should be extracted
   - Functions doing too many things (single responsibility)
   - Deep nesting that can be flattened with early returns
   - Missing type annotations
   - Missing or outdated docstrings
   - Mutable default arguments
   - Broad exception handling
4. **Refactor** one smell at a time, running tests after each change
5. **Verify**: `uv run mypy` + `uv run ruff check` + `uv run python -m pytest tests -v`
6. **Confirm** test count is equal or greater than baseline — no tests lost

Report what was refactored and why, with before/after for each change.
