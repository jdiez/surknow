# surknow

Agentic Domain Characterization Pipeline — takes structured domain descriptions and autonomously builds knowledge graphs through iterative deepening across 6 stages.

## Overview

**surknow** is an autonomous knowledge-graph construction system. Given a domain description with seed entities and relationships, it orchestrates a team of LLM agents to iteratively explore, extract, and structure domain knowledge into a queryable graph in SurrealDB.

## Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11+ / uv |
| Orchestration | Prefect 3.x |
| Agents | Agno (structured output) + Claude Code SDK (web search) |
| Graph DB | SurrealDB (graph + document) |
| LLM | AWS Bedrock Claude (via AI Gateway) |
| CLI | Typer + Rich |
| Models | Pydantic v2 |

## Quick Start

```bash
# Install
uv sync

# Configure
cp .env.example .env  # Fill in credentials

# Run a domain characterization (full pipeline with SurrealDB)
uv run domain-kg run examples/input_vorex_multi_cancer.yaml -c config/vorex_multi_cancer.yaml

# Run characterization with text output (no DB required, supports resume)
uv run domain-kg characterize examples/input_vorex_multi_cancer.yaml -o output/vorex

# SDK-powered exploration with real web search (no DB required, default)
uv run domain-kg explore examples/input_vorex_multi_cancer.yaml -o output/vorex_sdk

# Run all 3 exploration stages
uv run domain-kg explore examples/input_vorex_multi_cancer.yaml -o output/vorex_sdk --stage 3

# Use Agno backend instead of SDK (requires Bedrock)
uv run domain-kg explore examples/input_vorex_multi_cancer.yaml --no-sdk

# Resume a previous run (skips completed stages automatically)
uv run domain-kg characterize examples/input_vorex_multi_cancer.yaml -o output/vorex

# Force fresh run (ignores cached stages)
uv run domain-kg characterize examples/input_vorex_multi_cancer.yaml -o output/vorex --fresh

# Check pipeline status
uv run domain-kg status "Multi-Cancer Early Detection"

# Export the knowledge graph
uv run domain-kg export "Multi-Cancer Early Detection" --format text -o export.txt
```

### Prerequisites

- Python 3.11+
- SurrealDB running locally (or remote URL configured) — only needed for `run`/`status`/`export`
- AWS Bedrock access (direct or via AI Gateway)
- Prefect server (optional, for flow tracking)

## Architecture

```
Input (YAML/CSV/text)
    │
    ▼
┌─────────────────────────────────────────────────────┐
│  Stage 1: Domain Understanding                       │
│  Expand description, classify entities, boundaries   │
├─────────────────────────────────────────────────────┤
│  Stage 2: Branch Discovery                           │
│  Hierarchical sub-field decomposition                │
├─────────────────────────────────────────────────────┤
│  Stage 3: Vocabulary Gathering          ◄── iterate │
│  Domain-specific terminology per branch              │
├─────────────────────────────────────────────────────┤
│  Stage 4: Search Planning                            │
│  Targeted queries by coverage gap                    │
├─────────────────────────────────────────────────────┤
│  Stage 5: Entity & Link Extraction                   │
│  Parallel extraction + confidence scoring            │
├─────────────────────────────────────────────────────┤
│  Stage 6: Graph Construction                         │
│  Dedup, merge, write to SurrealDB                    │
└─────────────────────────────────────────────────────┘
    │
    ▼
SurrealDB Knowledge Graph
```

Stages 2-5 iterate until coverage threshold (default 80%) or max iterations reached.

## Input Formats

| Format | Extension | Best for |
|--------|-----------|----------|
| YAML | `.yaml` | Rich structured input with metadata |
| CSV/TSV | `.csv`, `.tsv` | Bulk entity/relationship import |
| Plain text | `.txt` | Quick domain descriptions |

See `examples/` for samples of each format.

## CLI Commands

| Command | Description |
|---------|-------------|
| `run` | Full pipeline: parse → agents → SurrealDB write |
| `characterize` | Stages 1-4 with text file output and resume support |
| `explore` | Domain exploration with web search — SDK default, `--no-sdk` for Agno |
| `status` | Show graph entity/relationship counts and branch coverage |
| `export` | Export graph as JSON, CSV, or human-readable text |

## Configuration

| File | Purpose |
|------|---------|
| `.env` | Infrastructure credentials (DB, API keys, AWS) |
| `config/*.yaml` | Domain-specific settings (references, tools, examples) |

All settings use the `DKG_` env prefix. See `.env.example` for full list.

## Project Structure

```
surknow/
├── src/domain_kg/
│   ├── models.py           # Pydantic models (18 types)
│   ├── config.py           # Settings (pydantic-settings)
│   ├── domain_config.py    # Domain YAML config loader
│   ├── cli.py              # Typer CLI
│   ├── parsers/            # Input parsing (YAML, CSV, text)
│   ├── flows/              # Prefect flows (6 pipeline stages)
│   ├── agents/             # Agno agent definitions + tools
│   └── db/                 # SurrealDB client, schema, queries
├── config/                 # Domain configuration files
├── examples/               # Example input files
└── tests/                  # pytest test suite
```

## Development

```bash
uv sync
uv run pytest
uv run mypy src/
uv run ruff check .
```

## License

MIT
