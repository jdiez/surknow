"""Stage 3: Graph Construction via Graph Team."""

from __future__ import annotations

from pathlib import Path

import structlog
import yaml
from prefect import task

from domain_kg.agents.teams import build_graph_team
from domain_kg.config import Settings
from domain_kg.domain_config import DomainConfig
from domain_kg.models import CoverageMetrics, Entity, GraphResult, Relationship

logger = structlog.get_logger("domain_kg.flows.construct")


@task(name="run-graph-team")
async def run_graph_team(
    entities: list[Entity],
    relationships: list[Relationship],
    domain_config: DomainConfig,
    settings: Settings,
    output_dir: Path = Path("output"),
    run_id: str = "",
) -> GraphResult:
    """Run the Graph Team to deduplicate, validate, and assess coverage."""
    logger.info("graph_team.started", entities=len(entities), relationships=len(relationships))

    team = build_graph_team(settings)

    entity_summary = "\n".join(
        f"  - {e.name} ({e.entity_type.value}): {e.description or ''}"
        for e in entities[:100]
    )
    rel_summary = "\n".join(
        f"  - {r.source} --[{r.relation_type}]--> {r.target} (conf: {r.confidence})"
        for r in relationships[:100]
    )

    entity_types = domain_config.get_entity_types()
    relation_types = domain_config.get_relation_types()

    prompt = (
        f"Process these {len(entities)} entities and {len(relationships)} relationships "
        f"for the '{domain_config.domain}' knowledge graph.\n\n"
        f"Allowed entity types: {', '.join(entity_types)}\n"
        f"Allowed relation types: {', '.join(relation_types)}\n\n"
        f"ENTITIES:\n{entity_summary}\n\n"
        f"RELATIONSHIPS:\n{rel_summary}\n\n"
        "Deduplicate, validate against ontology, and assess coverage."
    )

    try:
        response = await team.arun(prompt)
        result = response.content

        if not isinstance(result, GraphResult):
            result = GraphResult(
                entities=entities,
                relationships=relationships,
                coverage=CoverageMetrics(
                    branches_covered=len({e.branch for e in entities if e.branch}),
                    total_branches=len(domain_config.get_entity_types()) or 1,
                    coverage_pct=0.5,
                    entities_total=len(entities),
                    relationships_total=len(relationships),
                ),
            )
    except Exception as e:
        logger.error("graph_team.failed", error=str(e))
        result = GraphResult(
            entities=entities,
            relationships=relationships,
            coverage=CoverageMetrics(
                branches_covered=len({e.branch for e in entities if e.branch}),
                total_branches=len(domain_config.get_entity_types()) or 1,
                coverage_pct=0.5,
                entities_total=len(entities),
                relationships_total=len(relationships),
            ),
        )

    _save_graph_results(result, output_dir, run_id)

    logger.info(
        "graph_team.complete",
        entities=len(result.entities),
        relationships=len(result.relationships),
        merges=result.merges_performed,
        coverage=result.coverage.coverage_pct,
        gaps=len(result.gaps),
    )

    return result


@task(name="persist-graph")
async def persist_graph(result: GraphResult, settings: Settings) -> None:
    """Persist validated graph to SurrealDB."""
    logger.info("persist.started", entities=len(result.entities), rels=len(result.relationships))

    from domain_kg.db.client import get_client
    from domain_kg.db.queries import QueryHelper

    async with get_client(settings) as client:
        helper = QueryHelper(client)

        for entity in result.entities:
            existing = await helper.find_entity_by_name(entity.name)
            if not existing:
                await helper.create_entity(entity)

        for rel in result.relationships:
            await helper.create_relationship(rel)

    logger.info("persist.complete")


def _save_graph_results(result: GraphResult, output_dir: Path, run_id: str) -> None:
    """Save graph team output."""
    graph_dir = output_dir / run_id / "graph"
    graph_dir.mkdir(parents=True, exist_ok=True)

    merged_path = graph_dir / "merged_entities.yaml"
    merged_data = [
        {
            "name": e.name,
            "type": e.entity_type.value,
            "description": e.description or "",
            "branch": e.branch or "",
            "aliases": e.aliases,
        }
        for e in result.entities
    ]
    merged_path.write_text(
        yaml.dump(merged_data, default_flow_style=False, sort_keys=False, allow_unicode=True)
    )

    coverage_path = graph_dir / "coverage_report.yaml"
    coverage_data = {
        "coverage_pct": result.coverage.coverage_pct,
        "branches_covered": result.coverage.branches_covered,
        "total_branches": result.coverage.total_branches,
        "entities_total": result.coverage.entities_total,
        "relationships_total": result.coverage.relationships_total,
        "merges_performed": result.merges_performed,
        "entities_rejected": result.entities_rejected,
        "gaps": result.gaps,
    }
    coverage_path.write_text(
        yaml.dump(coverage_data, default_flow_style=False, sort_keys=False)
    )
