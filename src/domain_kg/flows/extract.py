"""Stage 2: Search Execution & Extraction Team."""

from __future__ import annotations

import json
from pathlib import Path

import structlog
import yaml
from prefect import task

from domain_kg.agents.teams import build_extraction_team
from domain_kg.config import Settings
from domain_kg.domain_config import DomainConfig
from domain_kg.models import Entity, Relationship, SearchPlan
from domain_kg.search.executor import execute_search_plan
from domain_kg.search.models import SearchExecutionReport, SearchResultItem

logger = structlog.get_logger("domain_kg.flows.extract")


def _build_ontology_prompt(domain_config: DomainConfig) -> str:
    """Build ontology constraint prompt for the extraction team."""
    lines = []
    entity_types = domain_config.get_entity_types()
    if entity_types:
        lines.append(f"Allowed entity types: {', '.join(entity_types)}")

    relation_types = domain_config.get_relation_types()
    if relation_types:
        lines.append(f"Allowed relation types: {', '.join(relation_types)}")

    extra = domain_config.get_extraction_instructions()
    if extra:
        lines.append("\nExtraction rules:")
        for instruction in extra:
            lines.append(f"  - {instruction}")

    return "\n".join(lines)


def _format_items_for_extraction(items: list[SearchResultItem], branch: str) -> str:
    """Format search result items as context for extraction."""
    parts = []
    for i, item in enumerate(items[:20], 1):
        content = item.content or item.snippet or ""
        if len(content) > 2000:
            content = content[:2000] + "..."
        parts.append(
            f"--- Document {i} ---\n"
            f"Title: {item.title}\n"
            f"URL: {item.url}\n"
            f"Branch: {branch}\n"
            f"Content: {content}\n"
        )
    return "\n".join(parts)


@task(name="run-extraction-team")
async def run_extraction_team(
    report: SearchExecutionReport,
    domain_config: DomainConfig,
    settings: Settings,
    output_dir: Path = Path("output"),
    run_id: str = "",
) -> tuple[list[Entity], list[Relationship]]:
    """Run the Extraction Team on search results grouped by branch."""
    logger.info("extraction_team.started", total_items=report.total_items)

    ontology_prompt = _build_ontology_prompt(domain_config)
    team = build_extraction_team(settings, ontology_prompt)

    all_entities: list[Entity] = []
    all_relationships: list[Relationship] = []

    branch_items: dict[str, list[SearchResultItem]] = {}
    for result in report.results:
        if result.skipped or result.error:
            continue
        branch = result.query.split("|")[0].strip() if "|" in result.query else "general"
        for item in result.items:
            if item.content or item.snippet:
                branch_items.setdefault(branch, []).append(item)

    for branch, items in branch_items.items():
        if not items:
            continue

        logger.info("extraction_team.processing_branch", branch=branch, items=len(items))

        formatted = _format_items_for_extraction(items, branch)
        prompt = (
            f"Extract entities and relationships from these {len(items)} documents "
            f"about '{branch}':\n\n{formatted}"
        )

        try:
            response = await team.arun(prompt)
            content = response.content

            if hasattr(content, "entities"):
                all_entities.extend(content.entities)
            if hasattr(content, "relationships"):
                all_relationships.extend(content.relationships)
        except Exception as e:
            logger.error("extraction_team.branch_failed", branch=branch, error=str(e))
            continue

    _save_extraction_results(all_entities, all_relationships, output_dir, run_id)

    logger.info(
        "extraction_team.complete",
        entities=len(all_entities),
        relationships=len(all_relationships),
    )

    return all_entities, all_relationships


@task(name="execute-searches")
async def execute_searches(
    search_plan: SearchPlan,
    settings: Settings,
    domain_config: DomainConfig,
    run_id: str = "",
    output_dir: Path = Path("output"),
    dry_run: bool = False,
) -> SearchExecutionReport:
    """Execute the search plan and return raw results."""
    logger.info("search_execution.started", queries=len(search_plan.queries), dry_run=dry_run)

    report = await execute_search_plan(
        search_plan=search_plan,
        settings=settings,
        domain_config=domain_config,
        run_id=run_id,
        output_dir=output_dir,
        dry_run=dry_run,
    )

    logger.info(
        "search_execution.complete",
        total_queries=report.total_queries,
        total_items=report.total_items,
    )

    return report


def _save_extraction_results(
    entities: list[Entity],
    relationships: list[Relationship],
    output_dir: Path,
    run_id: str,
) -> None:
    """Persist extraction results as JSON (audit) and YAML (human-readable)."""
    extractions_dir = output_dir / run_id / "extractions"
    extractions_dir.mkdir(parents=True, exist_ok=True)

    entities_path = extractions_dir / "entities.json"
    entities_path.write_text(
        json.dumps([e.model_dump(mode="json") for e in entities], indent=2)
    )

    rels_path = extractions_dir / "relationships.json"
    rels_path.write_text(
        json.dumps([r.model_dump(mode="json") for r in relationships], indent=2)
    )

    by_type: dict[str, list[dict]] = {}
    for e in entities:
        type_key = e.entity_type.value
        by_type.setdefault(type_key, []).append({
            "name": e.name,
            "description": e.description or "",
            "branch": e.branch or "",
            "confidence": e.provenance.confidence,
            "source": e.provenance.source,
            **({"aliases": e.aliases} if e.aliases else {}),
        })

    for type_key in by_type:
        by_type[type_key].sort(key=lambda x: x["confidence"], reverse=True)

    entities_yaml_path = extractions_dir / "entities.yaml"
    entities_yaml_path.write_text(
        yaml.dump(by_type, default_flow_style=False, sort_keys=False, allow_unicode=True)
    )

    by_rel: dict[str, list[dict]] = {}
    for r in relationships:
        by_rel.setdefault(r.relation_type, []).append({
            "source": r.source,
            "target": r.target,
            "confidence": r.confidence,
        })

    for rel_type in by_rel:
        by_rel[rel_type].sort(key=lambda x: x["confidence"], reverse=True)

    rels_yaml_path = extractions_dir / "relationships.yaml"
    rels_yaml_path.write_text(
        yaml.dump(by_rel, default_flow_style=False, sort_keys=False, allow_unicode=True)
    )
