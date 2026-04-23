Implement a feature or fix using spec-driven TDD. Argument: $ARGUMENTS (spec/issue description)

Follow this workflow strictly:

1. **Decompose** the spec into discrete, testable requirements
2. **Write tests first** in `tests/` for each requirement — tests MUST fail initially
3. **Implement** the minimum code to make each test pass, one at a time
4. **Verify types**: Run `uv run mypy` after each module change
5. **Verify lint**: Run `uv run ruff check --fix` and `uv run ruff format`
6. **Run full suite**: `uv run python -m pytest tests -v` — all tests must pass
7. **Design review** — before finalizing, check each new file against Design Principles:
   - **Paradigm**: Classes used for stateful entities? Functions for pure transforms? No single-method classes that should be functions?
   - **Patterns**: Applied only where they solve real complexity? No premature abstraction? Protocols over deep inheritance?
   - **Concurrency**: async only for I/O-bound? multiprocessing for CPU-bound? sync by default unless measured need?
   - **Error handling**: Specific exceptions? Validation at boundaries only? No bare `except`?
8. **Convention review** — verify project standards:
   - Type annotations on all public functions
   - Google-style docstrings on all public functions/classes
   - structlog logger if the module does any logging
   - Pydantic models use `frozen=True`
   - No `list` where `tuple` should be used for immutable collections

Report a summary of what was implemented, tests added, and design decisions made (which paradigm/pattern chosen and why).
