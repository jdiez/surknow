"""Stage 4: Search Planning."""

from __future__ import annotations

import structlog
from prefect import task

from domain_kg.config import Settings
from domain_kg.models import BranchTree, SearchPlan, VocabularyIndex

logger = structlog.get_logger("domain_kg.flows.search")


@task(name="plan-searches")
async def plan_searches(
    branches: BranchTree,
    vocabulary: VocabularyIndex,
    settings: Settings,
) -> SearchPlan:
    """Stage 4: Generate targeted search queries prioritized by coverage gaps."""
    from domain_kg.agents.definitions import search_strategist

    logger.info("stage4.started", branches=len(branches.branches), terms=len(vocabulary.terms))

    prompt = (
        f"Plan search queries to discover entities in this domain.\n\n"
        f"Branches: {[b.name for b in branches.branches]}\n"
        f"Vocabulary terms: {[t.canonical for t in vocabulary.terms[:50]]}\n"
        f"Coverage gaps: branches with coverage < {settings.coverage_threshold}\n\n"
        f"Generate structured queries per branch, prioritizing least-covered branches. "
        f"Plan sources: academic, industry, repos, patents."
    )

    response = await search_strategist.arun(prompt)
    if response and response.content:
        logger.info("stage4.completed", queries=len(response.content.queries))
        return response.content

    return SearchPlan(queries=[], total_branches=len(branches.branches), covered_branches=0)
