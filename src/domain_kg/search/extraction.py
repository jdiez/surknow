"""Ontology-driven entity extraction from search results via Agno structured output."""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from pydantic import BaseModel, Field

from domain_kg.config import Settings
from domain_kg.domain_config import DomainConfig
from domain_kg.models import Entity, EntityType, Provenance, Relationship, SearchQuery
from domain_kg.search.models import SearchResultItem

logger = structlog.get_logger("domain_kg.search.extraction")


class ExtractedEntity(BaseModel):
    """Single entity extracted by the LLM."""

    name: str
    entity_type: str
    description: str = ""
    confidence: float = Field(ge=0.0, le=1.0)
    aliases: list[str] = []


class ExtractedRelationship(BaseModel):
    """Single relationship extracted by the LLM."""

    source: str
    target: str
    relation_type: str
    confidence: float = Field(ge=0.0, le=1.0)


class ExtractionResult(BaseModel):
    """Structured output schema for the extraction agent."""

    entities: list[ExtractedEntity] = []
    relationships: list[ExtractedRelationship] = []


def _build_extraction_prompt(
    item: SearchResultItem,
    query: SearchQuery,
    domain_config: DomainConfig,
) -> str:
    """Build ontology-driven extraction prompt from domain config."""
    entity_types = _get_entity_types(domain_config)
    relation_types = _get_relation_types(domain_config)
    extra_instructions = _get_extraction_instructions(domain_config)

    content = item.content or item.snippet
    if len(content) > 4000:
        content = content[:4000]

    prompt = f"""Extract entities and relationships from this document.

Document Title: {item.title}
Source URL: {item.url}
Provider: {item.provider}
Content:
{content}

---

Branch context: {query.branch}
Expected entity types for this query: {', '.join(query.expected_entity_types)}

ONTOLOGY CONSTRAINTS:
- Valid entity types: {', '.join(entity_types)}
- Valid relationship types: {', '.join(relation_types)}

Only extract entities that match the valid entity types above.
Only extract relationships that match the valid relationship types above.
Score confidence 0.0-1.0 for each extraction based on how clearly the text supports it.
"""

    if extra_instructions:
        prompt += "\nDOMAIN-SPECIFIC INSTRUCTIONS:\n"
        for instruction in extra_instructions:
            prompt += f"- {instruction}\n"

    return prompt


def _get_entity_types(domain_config: DomainConfig) -> list[str]:
    """Extract unique entity types from domain config examples."""
    types = set()
    for entity in domain_config.examples.get("entities", []):
        types.add(entity.get("type", ""))
    for t in EntityType:
        types.add(t.value)
    types.discard("")
    return sorted(types)


def _get_relation_types(domain_config: DomainConfig) -> list[str]:
    """Extract unique relation types from domain config examples."""
    rels = set()
    for rel in domain_config.examples.get("relationships", []):
        rels.add(rel.get("relation", ""))
    rels.discard("")
    return sorted(rels)


def _get_extraction_instructions(domain_config: DomainConfig) -> list[str]:
    """Get per-type extraction instructions from agent_config."""
    agent_cfg = domain_config.agent_config.get("entity_extractor", {})
    return agent_cfg.get("extra_instructions", [])


def _resolve_entity_type(type_str: str) -> EntityType:
    """Map extracted type string to EntityType enum, falling back to custom."""
    try:
        return EntityType(type_str.lower())
    except ValueError:
        return EntityType.custom


async def extract_from_document(
    item: SearchResultItem,
    query: SearchQuery,
    domain_config: DomainConfig,
    settings: Settings,
) -> tuple[list[Entity], list[Relationship]]:
    """Extract entities and relationships from a single search result using LLM."""
    from agno.agent import Agent

    from domain_kg.agents.definitions import bedrock_claude

    prompt = _build_extraction_prompt(item, query, domain_config)

    extractor = Agent(
        name="DocumentExtractor",
        model=bedrock_claude,
        description="Extracts structured entities and relationships from documents.",
        instructions=["Extract entities and relationships according to the ontology constraints provided."],
        output_schema=ExtractionResult,
        markdown=False,
    )

    try:
        response = await extractor.arun(prompt)
    except Exception as e:
        logger.warning(
            "extraction.failed",
            url=item.url,
            error=str(e),
        )
        return [], []

    if not response or not response.content:
        return [], []

    result: ExtractionResult = response.content
    now = datetime.now(UTC)

    entities = []
    for ext_entity in result.entities:
        if ext_entity.confidence < settings.confidence_threshold:
            continue
        entities.append(
            Entity(
                name=ext_entity.name,
                entity_type=_resolve_entity_type(ext_entity.entity_type),
                description=ext_entity.description,
                branch=query.branch,
                aliases=ext_entity.aliases,
                provenance=Provenance(
                    source=item.url,
                    timestamp=now,
                    agent="DocumentExtractor",
                    model=settings.bedrock_model_id,
                    search_query=query.query,
                    confidence=ext_entity.confidence,
                ),
            )
        )

    relationships = []
    for ext_rel in result.relationships:
        if ext_rel.confidence < settings.confidence_threshold:
            continue
        relationships.append(
            Relationship(
                source=ext_rel.source,
                target=ext_rel.target,
                relation_type=ext_rel.relation_type,
                confidence=ext_rel.confidence,
                provenance=Provenance(
                    source=item.url,
                    timestamp=now,
                    agent="DocumentExtractor",
                    model=settings.bedrock_model_id,
                    search_query=query.query,
                    confidence=ext_rel.confidence,
                ),
            )
        )

    logger.info(
        "extraction.complete",
        url=item.url[:60],
        entities=len(entities),
        relationships=len(relationships),
    )

    return entities, relationships
