# Changelog

All notable changes to this project will be documented in this file.

## [0.6.1] - 2026-05-18

### Fixed

- SDK agents no longer fail due to PAI/CLAUDE.md skill interference in subprocess
- Root cause: SDK subprocess loaded global CLAUDE.md, triggering PAI ALGORITHM mode and
  skill invocations that burned agent turns and prevented JSON output
- Fix: headless subprocess preamble in append_system_prompt that disables mode/skill triggers
- Added ToolSearch to allowed tools so agent can self-load WebFetch when WebSearch unavailable
- Improved text block collection: scans all blocks for JSON instead of keeping only last one
- Graceful error handling when SDK subprocess crashes mid-stream (preserves partial results)
- Result: 0 failed batches in vocabulary (was 4/6), all stages succeed consistently

## [0.6.0] - 2026-05-18

### Changed

- SDK is now the default backend for `explore` command (was opt-in)
- `explore` now runs all 3 stages by default (`--stage 3`)
- Added `--no-sdk` flag to fall back to Agno backend
- `use_sdk` config default changed to `true`
- Explore command displays backend label in progress output

## [0.5.2] - 2026-05-18

### Added

- Claude Code SDK integration for Stage 3: Vocabulary Gathering (`gather_vocabulary_sdk()`)
- `explore --stage 3` gathers domain terminology with web-grounded research
- Batched vocabulary collection (6 branches per SDK call) for reliability
- Partial-success resilience: failed batches are skipped, successful ones retained
- Resume-from-cache support for Stage 3 (`.state/vocabulary_sdk.json`)

### Changed

- `gather_vocabulary()` now accepts `use_sdk` and `domain` parameters
- SDK vocabulary timeout increased to 180s per batch

## [0.5.1] - 2026-05-18

### Added

- Claude Code SDK integration for Stage 2: Branch Discovery (`discover_branches_sdk()`)
- `explore --stage 2` now discovers domain branches with web-grounded research
- Branch tree output with hierarchical depth, confidence, and descriptions
- Resume-from-cache support for Stage 2 (`.state/branches_sdk.json`)

### Changed

- `discover_branches()` now accepts `use_sdk` parameter for backend selection
- `explore` command runs stages sequentially up to `--stage` value

## [0.5.0] - 2026-05-18

### Added

- Claude Code SDK integration for web-grounded domain exploration (Phase 1)
- `domain-kg explore` CLI command — SDK-powered Stage 1 with real web search
- `sdk_explorer.py` agent module: `understand_domain_sdk()` with JSON extraction
- SDK agents use `bypassPermissions` mode with `WebSearch` + `Read` tools only
- Automatic fallback to Agno backend when SDK is unavailable or fails
- `use_sdk` config option (`DKG_USE_SDK=true`) for toggling SDK usage
- Resume-from-cache support in `explore` command (`.state/understand_sdk.json`)

### Changed

- `understand_domain()` now accepts `use_sdk` parameter for backend selection
- Added `claude-code-sdk>=0.0.25` dependency

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
