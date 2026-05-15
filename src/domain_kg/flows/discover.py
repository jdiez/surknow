"""Stage 2: Branch Discovery."""

from __future__ import annotations

import structlog
from prefect import task

from domain_kg.models import BranchTree, DomainContext

logger = structlog.get_logger("domain_kg.flows.discover")


@task(name="discover-branches")
async def discover_branches(context: DomainContext, iteration: int) -> BranchTree:
    """Stage 2: Decompose domain into hierarchical branches."""
    from domain_kg.agents.definitions import branch_explorer

    logger.info("stage2.started", domain=context.domain, iteration=iteration)

    prompt = (
        f"Decompose this domain into hierarchical branches (sub-fields).\n\n"
        f"Domain: {context.domain}\n"
        f"Description: {context.description}\n"
        f"Boundaries: {context.boundaries}\n"
        f"Existing entity types: {context.initial_entity_types}\n"
        f"Iteration: {iteration}\n\n"
        f"Produce a branch tree with confidence scores and coverage estimates."
    )

    response = await branch_explorer.arun(prompt)
    if response and response.content:
        logger.info("stage2.completed", branches=len(response.content.branches))
        return response.content

    return BranchTree(branches=[], coverage_pct=0.0, iteration=iteration)
