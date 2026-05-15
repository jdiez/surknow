"""Main orchestrator flow for domain characterization."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import structlog
from prefect import flow

from domain_kg.config import Settings
from domain_kg.flows.construct import construct_graph
from domain_kg.flows.discover import discover_branches
from domain_kg.flows.extract import extract_entities
from domain_kg.flows.search import plan_searches
from domain_kg.flows.understand import understand_domain
from domain_kg.flows.vocabulary import gather_vocabulary
from domain_kg.models import KGResult
from domain_kg.parsers import parse_input

logger = structlog.get_logger("domain_kg.flows.main")


@flow(name="domain-characterize", retries=1)
async def characterize_domain(input_file: Path, settings: Settings | None = None) -> KGResult:
    """Main orchestrator flow for domain characterization."""
    if settings is None:
        settings = Settings()

    domain_input = await parse_input(input_file)
    run_id = f"{domain_input.domain}_{datetime.now(tz=timezone.utc).isoformat()}"

    logger.info("pipeline.started", domain=domain_input.domain, run_id=run_id)

    context = await understand_domain(domain_input)

    total_entities = 0
    total_relations = 0
    iterations_used = 0

    for iteration in range(settings.max_iterations):
        iterations_used = iteration + 1
        logger.info("iteration.started", iteration=iteration, domain=domain_input.domain)

        branches = await discover_branches(context, iteration)
        vocabulary = await gather_vocabulary(branches, settings)
        search_plan = await plan_searches(branches, vocabulary, settings)
        entities, relations = await extract_entities(search_plan, settings)
        coverage = await construct_graph(entities, relations, context, settings)

        total_entities += len(entities)
        total_relations += len(relations)

        if coverage.meets_threshold(settings.coverage_threshold):
            logger.info("coverage.threshold_met", coverage=coverage.coverage_pct)
            break

    return KGResult(
        entities_created=total_entities,
        relationships_created=total_relations,
        entities_merged=0,
        branches_covered=coverage.branches_covered,
        total_branches=coverage.total_branches,
        coverage_pct=coverage.coverage_pct,
        iterations_used=iterations_used,
        schema_discovered=[],
    )
