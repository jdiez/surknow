# CLAUDE.md

## What This Is

**surknow** — Agentic Domain Characterization Pipeline. Takes structured domain descriptions (YAML/CSV/text with seed entities and relationships) and autonomously builds knowledge graphs through 6 iterative stages.

## Stack

- Python 3.11+, uv package management
- Prefect 3.x (flow orchestration)
- Agno (multi-agent framework with structured output)
- SurrealDB (multi-model graph + document DB)
- AWS Bedrock Claude (LLM inference)
- Typer + Rich (CLI)
- Pydantic v2 (models and settings)

## Project Structure

```
surknow/
├── pyproject.toml
├── src/domain_kg/
│   ├── __init__.py
│   ├── models.py           # All Pydantic models
│   ├── config.py           # Settings (env vars, DKG_ prefix)
│   ├── domain_config.py    # YAML domain config loader
│   ├── cli.py              # Typer CLI (run, status, export)
│   ├── parsers/            # Input parsing (YAML, CSV, text)
│   ├── flows/              # Prefect flows (6 pipeline stages)
│   ├── agents/             # Agno agent definitions + tools
│   └── db/                 # SurrealDB client, schema, queries
├── config/                 # Domain config files
├── examples/               # Example input files
├── tests/                  # pytest tests
└── references/             # Local reference documents
```

## Development

```bash
uv sync
uv run pytest
uv run mypy src/
uv run ruff check .
uv run domain-kg run examples/input_cancer_immunotherapy.yaml --dry-run
```

## Key Patterns

- All agents use Agno with `response_model` for structured Pydantic output
- ProcessingLog in SurrealDB enables incremental runs (skip already-processed data)
- ToolRegistry resolves domain-specific tools at runtime per agent
- Flows are async Prefect tasks with retry support
- Coverage metrics drive iteration termination (threshold default 0.8)
