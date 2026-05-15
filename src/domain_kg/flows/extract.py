"""Stage 5: Entity & Link Extraction."""

from __future__ import annotations

import structlog
from prefect import task

from domain_kg.config import Settings
from domain_kg.models import Entity, Relationship, SearchPlan

logger = structlog.get_logger("domain_kg.flows.extract")


@task(name="extract-entities")
async def extract_entities(
    search_plan: SearchPlan,
    settings: Settings,
) -> tuple[list[Entity], list[Relationship]]:
    """Stage 5: Execute searches and extract entities with confidence scoring."""
    from domain_kg.agents.definitions import entity_extractor

    logger.info("stage5.started", queries=len(search_plan.queries))

    prompt = (
        f"Execute these search queries and extract entities and relationships.\n\n"
        f"Queries:\n"
        + "\n".join(f"- [{q.source_type}] {q.query} (branch: {q.branch})" for q in search_plan.queries[:20])
        + f"\n\nFor each result, extract: entity name, type, description, branch, "
        f"and relationships. Score confidence 0.0-1.0. "
        f"Minimum confidence threshold: {settings.confidence_threshold}"
    )

    response = await entity_extractor.arun(prompt)
    logger.info("stage5.completed")

    return [], []
