"""Stage 6: Graph Construction & Resolution."""

from __future__ import annotations

import structlog
from prefect import task

from domain_kg.config import Settings
from domain_kg.models import CoverageMetrics, DomainContext, Entity, Relationship

logger = structlog.get_logger("domain_kg.flows.construct")


@task(name="construct-graph")
async def construct_graph(
    entities: list[Entity],
    relations: list[Relationship],
    context: DomainContext,
    settings: Settings,
) -> CoverageMetrics:
    """Stage 6: Deduplicate, merge, and write to SurrealDB."""
    logger.info("stage6.started", entities=len(entities), relations=len(relations))

    from domain_kg.db.client import get_client
    from domain_kg.db.queries import QueryHelper

    async with get_client(settings) as client:
        helper = QueryHelper(client)

        for entity in entities:
            existing = await helper.find_entity_by_name(entity.name)
            if not existing:
                await helper.create_entity(entity)

        for rel in relations:
            await helper.create_relationship(rel)

        branch_coverage = await helper.get_branch_coverage()
        entity_count = await helper.get_entity_count()
        rel_count = await helper.get_relationship_count()

    branches_covered = len(branch_coverage)
    total_branches = len(context.initial_entity_types) or 1

    logger.info("stage6.completed", entities=entity_count, relations=rel_count)

    return CoverageMetrics(
        branches_covered=branches_covered,
        total_branches=total_branches,
        coverage_pct=branches_covered / total_branches if total_branches > 0 else 0.0,
        entities_total=entity_count,
        relationships_total=rel_count,
    )
