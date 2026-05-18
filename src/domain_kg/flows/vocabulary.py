"""Stage 3: Vocabulary Gathering."""

from __future__ import annotations

import structlog
from prefect import task

from domain_kg.config import Settings
from domain_kg.models import BranchTree, VocabularyIndex

logger = structlog.get_logger("domain_kg.flows.vocabulary")


@task(name="gather-vocabulary")
async def gather_vocabulary(
    branches: BranchTree, settings: Settings, domain: str = "", use_sdk: bool = False
) -> VocabularyIndex:
    """Stage 3: Gather domain-specific terminology per branch."""
    if use_sdk:
        return await _gather_sdk(branches, domain)
    return await _gather_agno(branches)


async def _gather_sdk(branches: BranchTree, domain: str) -> VocabularyIndex:
    """Stage 3 via Claude Code SDK — grounded with real web search."""
    from domain_kg.agents.sdk_explorer import gather_vocabulary_sdk

    logger.info("stage3.started", branch_count=len(branches.branches), backend="sdk")
    try:
        vocab = await gather_vocabulary_sdk(branches, domain)
        logger.info("stage3.completed", terms=len(vocab.terms), backend="sdk")
        return vocab
    except Exception as e:
        logger.warning("stage3.sdk_failed", error=str(e), fallback="agno")
        return await _gather_agno(branches)


async def _gather_agno(branches: BranchTree) -> VocabularyIndex:
    """Stage 3 via Agno agent — structured output, no tools."""
    from domain_kg.agents.definitions import vocabulary_collector

    logger.info("stage3.started", branch_count=len(branches.branches), backend="agno")

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
