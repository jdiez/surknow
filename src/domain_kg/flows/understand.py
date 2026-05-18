"""Stage 1: Domain Understanding."""

from __future__ import annotations

import structlog
from prefect import task

from domain_kg.models import DomainContext, DomainInput

logger = structlog.get_logger("domain_kg.flows.understand")


@task(name="understand-domain")
async def understand_domain(domain_input: DomainInput, use_sdk: bool = False) -> DomainContext:
    """Stage 1: Analyze domain and establish scope, boundaries, initial schema."""
    if use_sdk:
        return await _understand_sdk(domain_input)
    return await _understand_agno(domain_input)


async def _understand_sdk(domain_input: DomainInput) -> DomainContext:
    """Stage 1 via Claude Code SDK — grounded with real web search."""
    from domain_kg.agents.sdk_explorer import understand_domain_sdk

    logger.info("stage1.started", domain=domain_input.domain, backend="sdk")
    try:
        context = await understand_domain_sdk(domain_input)
        logger.info("stage1.completed", domain=domain_input.domain, backend="sdk")
        return context
    except Exception as e:
        logger.warning("stage1.sdk_failed", error=str(e), fallback="agno")
        return await _understand_agno(domain_input)


async def _understand_agno(domain_input: DomainInput) -> DomainContext:
    """Stage 1 via Agno agent — structured output, no tools."""
    from domain_kg.agents.definitions import domain_analyst

    logger.info("stage1.started", domain=domain_input.domain, backend="agno")

    prompt = (
        f"Analyze the following domain and produce a comprehensive context.\n\n"
        f"Domain: {domain_input.domain}\n"
        f"Description: {domain_input.description}\n\n"
        f"Seed entities: {[e.model_dump() for e in domain_input.entities]}\n"
        f"Seed links: {[l.model_dump() for l in domain_input.links]}\n\n"
        f"Produce: scope, boundaries, adjacent fields, initial entity types, "
        f"initial relation types."
    )

    response = await domain_analyst.arun(prompt)
    if response and response.content:
        logger.info("stage1.completed", domain=domain_input.domain, backend="agno")
        return response.content

    return DomainContext(
        domain=domain_input.domain,
        description=domain_input.description,
        boundaries=[],
        adjacent_fields=[],
        initial_entity_types=[e.type for e in domain_input.entities],
        initial_relation_types=[l.relation for l in domain_input.links],
        seed_entities=domain_input.entities,
        seed_links=domain_input.links,
    )
