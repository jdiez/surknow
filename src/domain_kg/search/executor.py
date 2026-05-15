"""Orchestrates execution of a full SearchPlan against providers."""

from __future__ import annotations

import asyncio
import hashlib
from datetime import UTC, datetime
from pathlib import Path

import structlog

from domain_kg.config import Settings
from domain_kg.domain_config import DomainConfig
from domain_kg.models import SearchPlan, SearchQuery
from domain_kg.search.dispatcher import SearchDispatcher
from domain_kg.search.models import SearchExecutionReport, SearchResult, SearchResultItem

logger = structlog.get_logger("domain_kg.search.executor")


def _query_hash(query: SearchQuery) -> str:
    key = f"{query.source_type}:{query.branch}:{query.query}"
    return hashlib.sha256(key.encode()).hexdigest()[:12]


def _result_path(output_dir: Path, run_id: str, query: SearchQuery) -> Path:
    return output_dir / run_id / "search_results" / f"{_query_hash(query)}.json"


async def execute_search_plan(
    search_plan: SearchPlan,
    settings: Settings,
    domain_config: DomainConfig,
    run_id: str,
    output_dir: Path,
    dry_run: bool = False,
) -> SearchExecutionReport:
    """Execute all queries in a SearchPlan, respecting rate limits and dedup."""
    dispatcher = SearchDispatcher(settings, domain_config)
    results_dir = output_dir / run_id / "search_results"
    results_dir.mkdir(parents=True, exist_ok=True)

    sorted_queries = sorted(search_plan.queries, key=lambda q: q.priority)

    if dry_run:
        logger.info("executor.dry_run", total_queries=len(sorted_queries))
        results = []
        for q in sorted_queries:
            providers = dispatcher.resolve_providers(q)
            provider_names = [p.name for p in providers]
            logger.info(
                "executor.dry_run.query",
                query=q.query[:60],
                source_type=q.source_type,
                branch=q.branch,
                providers=provider_names,
            )
            results.append(SearchResult(query=q, skipped=True))
        return SearchExecutionReport(
            total_queries=len(sorted_queries),
            executed=0,
            skipped=len(sorted_queries),
            failed=0,
            total_items=0,
            results=results,
        )

    priority_groups: dict[int, list[SearchQuery]] = {}
    for q in sorted_queries:
        priority_groups.setdefault(q.priority, []).append(q)

    all_results: list[SearchResult] = []
    executed = 0
    skipped = 0
    failed = 0
    total_items = 0

    semaphore = asyncio.Semaphore(settings.search_concurrent_queries)

    for priority in sorted(priority_groups.keys()):
        queries = priority_groups[priority]

        async def _execute_one(query: SearchQuery, sem: asyncio.Semaphore = semaphore) -> SearchResult:
            async with sem:
                return await _run_query(query, dispatcher, settings, results_dir)

        batch_results = await asyncio.gather(
            *[_execute_one(q) for q in queries], return_exceptions=True
        )

        for result in batch_results:
            if isinstance(result, Exception):
                logger.error("executor.query.exception", error=str(result))
                failed += 1
                continue
            all_results.append(result)
            if result.skipped:
                skipped += 1
            elif result.error:
                failed += 1
            else:
                executed += 1
                total_items += len(result.items)

    report = SearchExecutionReport(
        total_queries=len(sorted_queries),
        executed=executed,
        skipped=skipped,
        failed=failed,
        total_items=total_items,
        results=all_results,
    )

    report_path = output_dir / run_id / "execution_report.json"
    report_path.write_text(report.model_dump_json(indent=2))
    logger.info(
        "executor.complete",
        executed=executed,
        skipped=skipped,
        failed=failed,
        total_items=total_items,
    )

    return report


async def _run_query(
    query: SearchQuery,
    dispatcher: SearchDispatcher,
    settings: Settings,
    results_dir: Path,
) -> SearchResult:
    """Execute a single query, checking for existing results first."""
    result_file = results_dir / f"{_query_hash(query)}.json"

    if result_file.exists():
        logger.info("executor.query.skipped", query=query.query[:60], reason="already_executed")
        return SearchResult(query=query, skipped=True)

    providers = dispatcher.resolve_providers(query)
    if not providers:
        return SearchResult(query=query, error="no_providers_available")

    all_items: list[SearchResultItem] = []
    errors: list[str] = []

    for provider in providers:
        try:
            items = await provider.search(
                query=query.query,
                max_results=settings.search_max_results_per_query,
            )
            all_items.extend(items)
        except Exception as e:
            logger.warning(
                "executor.provider.error",
                provider=provider.name,
                query=query.query[:60],
                error=str(e),
            )
            errors.append(f"{provider.name}: {e}")

    result = SearchResult(
        query=query,
        items=all_items,
        executed_at=datetime.now(UTC),
        error="; ".join(errors) if errors and not all_items else None,
    )

    result_file.write_text(result.model_dump_json(indent=2))
    logger.info(
        "executor.query.complete",
        query=query.query[:60],
        items=len(all_items),
        providers=[p.name for p in providers],
    )

    return result
