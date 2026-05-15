"""Stage 3: Vocabulary Gathering."""

from __future__ import annotations

import structlog
from prefect import task

from domain_kg.config import Settings
from domain_kg.models import BranchTree, VocabularyIndex

logger = structlog.get_logger("domain_kg.flows.vocabulary")


@task(name="gather-vocabulary")
async def gather_vocabulary(branches: BranchTree, settings: Settings) -> VocabularyIndex:
    """Stage 3: Gather domain-specific terminology per branch."""
    from domain_kg.agents.definitions import vocabulary_collector

    logger.info("stage3.started", branch_count=len(branches.branches))

    branch_names = [b.name for b in branches.branches]
    prompt = (
        f"Gather domain-specific vocabulary for these branches:\n"
        f"{branch_names}\n\n"
        f"For each branch, extract key terms with definitions and aliases. "
        f"Normalize to canonical forms."
    )

    response = await vocabulary_collector.arun(prompt)
    if response and response.content:
        logger.info("stage3.completed", terms=len(response.content.terms))
        return response.content

    return VocabularyIndex(terms=[], branch_coverage={})
