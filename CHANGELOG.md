# Changelog

All notable changes to this project will be documented in this file.

## [0.4.0] - 2026-05-15

### Added

- Vorex multi-cancer early detection (MCED) domain configuration and input
- `domain-kg characterize` CLI command — runs stages 1-4 and outputs text files
- Disk-based resume: intermediate stage results cached in `.state/` directory
- `--fresh` flag to force re-execution of all stages
- Text export format for `domain-kg export`
- SurrealDB schema auto-detection (skip apply if tables exist)

### Changed

- SurrealDB client migrated to `AsyncSurreal` (proper async/await throughout)
- Default SurrealDB port changed to 8787
- Schema apply is now idempotent (checks for existing tables before applying)

### Fixed

- SurrealDB client connection error (`BlockingWsSurrealConnection` had no async `connect`)
- Query helper properly uses `await` with async client
- `export` command uses async client correctly

## [0.1.0] - 2026-05-15

### Added

- Complete 6-stage agentic domain characterization pipeline
- Agno agent definitions: DomainAnalyst, BranchExplorer, VocabularyCollector, SearchStrategist, EntityExtractor, GraphBuilder
- AI Gateway integration with async support (GatewayBedrock subclass)
- Prefect 3.x flow orchestration with iterative convergence
- SurrealDB client with async connection management, schema DDL, and typed queries
- Pydantic v2 models (18 types: EntityType, Entity, Relationship, Provenance, etc.)
- Input parsers: YAML, CSV/TSV, plain text
- Domain configuration system with tool registry and reference resolution
- Processing log for incremental runs (skip already-processed data)
- Typer CLI with `run`, `status`, and `export` commands
- Coverage-driven iteration termination (configurable threshold)
- Confidence scoring on all extracted entities and relationships
- Example domain configs: Cancer Immunotherapy, Knowledge Graphs
- pydantic-settings configuration with DKG_ env prefix
