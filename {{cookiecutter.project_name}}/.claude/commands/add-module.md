Create a new Python module with proper conventions. Argument: $ARGUMENTS (module name)

1. Create `src/{{cookiecutter.project_slug}}/$ARGUMENTS.py` (or flat layout equivalent) with:
   - Module docstring (Google style)
   - structlog logger: `logger = structlog.get_logger("{{cookiecutter.project_slug}}.$ARGUMENTS")`
   - Type annotations on all functions
2. Create matching test file `tests/test_$ARGUMENTS.py` with:
   - Import from the new module
   - At least one test function
3. Run `uv run ruff check --fix` and `uv run ruff format` on both files
4. Run `uv run mypy` to verify types pass
5. Run `uv run python -m pytest tests/test_$ARGUMENTS.py -v` to verify tests pass
