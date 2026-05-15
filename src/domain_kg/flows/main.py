"""Main orchestrator flow for domain characterization — agentic team pipeline."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import structlog
import yaml
from prefect import flow

from domain_kg.config import Settings
from domain_kg.domain_config import DomainConfig, load_domain_config
from domain_kg.flows.construct import persist_graph, run_graph_team
from domain_kg.flows.extract import execute_searches, run_extraction_team
from domain_kg.flows.research import brief_to_search_plan, run_research_team
from domain_kg.models import Entity, KGResult, Provenance, Relationship, RootEntity

logger = structlog.get_logger("domain_kg.flows.main")


@flow(name="domain-characterize", retries=1)
async def characterize_domain(
    input_file: Path | None = None,
    settings: Settings | None = None,
    domain_config: DomainConfig | None = None,
    config_path: Path | None = None,
    output_dir: Path = Path("output"),
    dry_run: bool = False,
) -> KGResult:
    """Main orchestrator: Research Team → Search → Extraction Team → Graph Team."""
    if settings is None:
        settings = Settings()

    if domain_config is None and config_path is not None:
        domain_config = load_domain_config(config_path)
    elif domain_config is None:
        domain_config = DomainConfig(domain="unknown", description="")

    run_id = f"{domain_config.domain}_{datetime.now(tz=UTC).strftime('%Y%m%d_%H%M%S')}"

    logger.info("pipeline.started", domain=domain_config.domain, run_id=run_id)

    all_entities: list[Entity] = []
    all_relationships: list[Relationship] = []
    iterations_used = 0

    for iteration in range(settings.max_iterations):
        iterations_used = iteration + 1
        logger.info("iteration.started", iteration=iteration, domain=domain_config.domain)

        # TEAM 1: Research — understand the domain
        brief = await run_research_team(domain_config, settings, output_dir, run_id)

        if dry_run:
            logger.info("pipeline.dry_run.complete", root_entities=len(brief.root_entities))
            break

        # Execute expansion plan searches (infrastructure-level, not agentic)
        search_plan = brief_to_search_plan(brief)
        report = await execute_searches(
            search_plan=search_plan,
            settings=settings,
            domain_config=domain_config,
            run_id=run_id,
            output_dir=output_dir,
        )

        # TEAM 2: Extraction — extract entities from search results
        entities, relationships = await run_extraction_team(
            report=report,
            domain_config=domain_config,
            settings=settings,
            output_dir=output_dir,
            run_id=run_id,
        )

        # Include root entities from research brief as high-confidence seeds
        root_entities = _convert_root_entities(brief.root_entities)
        entities = root_entities + entities

        # TEAM 3: Graph — deduplicate, validate, assess coverage
        graph_result = await run_graph_team(
            entities=entities,
            relationships=relationships,
            domain_config=domain_config,
            settings=settings,
            output_dir=output_dir,
            run_id=run_id,
        )

        all_entities.extend(graph_result.entities)
        all_relationships.extend(graph_result.relationships)

        # Persist to SurrealDB
        try:
            await persist_graph(graph_result, settings)
        except Exception as e:
            logger.warning("persist.skipped", error=str(e))

        # Check coverage
        if graph_result.coverage.meets_threshold(settings.coverage_threshold):
            logger.info("coverage.threshold_met", coverage=graph_result.coverage.coverage_pct)
            break

        # Feed gaps back for next iteration
        if graph_result.gaps:
            logger.info("iteration.gaps_found", gaps=graph_result.gaps)

    _save_final_output(all_entities, all_relationships, output_dir / run_id)

    coverage = graph_result.coverage if "graph_result" in dir() else None

    return KGResult(
        entities_created=len(all_entities),
        relationships_created=len(all_relationships),
        entities_merged=graph_result.merges_performed if "graph_result" in dir() else 0,
        branches_covered=coverage.branches_covered if coverage else 0,
        total_branches=coverage.total_branches if coverage else 0,
        coverage_pct=coverage.coverage_pct if coverage else 0.0,
        iterations_used=iterations_used,
        schema_discovered=[],
    )


def _convert_root_entities(root_entities: list[RootEntity]) -> list[Entity]:
    """Convert ResearchBrief root entities to pipeline Entity format."""
    from domain_kg.models import EntityType

    entities = []
    for re in root_entities:
        try:
            entity_type = EntityType(re.entity_type)
        except ValueError:
            entity_type = EntityType.custom

        entities.append(
            Entity(
                name=re.name,
                entity_type=entity_type,
                description=re.description,
                aliases=re.aliases,
                provenance=Provenance(
                    source=re.source_urls[0] if re.source_urls else "research_team",
                    agent="ResearchTeam",
                    model="opus-4",
                    confidence=re.confidence,
                ),
            )
        )
    return entities


def _save_final_output(
    entities: list[Entity],
    relationships: list[Relationship],
    output_dir: Path,
) -> None:
    """Save final pipeline output."""
    output_dir.mkdir(parents=True, exist_ok=True)

    summary = {
        "total_entities": len(entities),
        "total_relationships": len(relationships),
        "entity_types": list({e.entity_type.value for e in entities}),
        "branches": list({e.branch for e in entities if e.branch}),
    }

    summary_path = output_dir / "run_summary.yaml"
    summary_path.write_text(
        yaml.dump(summary, default_flow_style=False, sort_keys=False)
    )
