"""Typed query helpers for SurrealDB CRUD and RELATE operations."""

from __future__ import annotations

from typing import Any

import structlog

from domain_kg.db.client import SurrealClient
from domain_kg.models import Entity, Relationship

logger = structlog.get_logger("domain_kg.db.queries")


class QueryHelper:
    """Typed query helpers for common SurrealDB operations."""

    def __init__(self, client: SurrealClient) -> None:
        self._client = client

    async def create_entity(self, entity: Entity) -> Any:
        data = {
            "name": entity.name,
            "entity_type": entity.entity_type.value,
            "description": entity.description,
            "branch": entity.branch,
            "confidence": entity.provenance.confidence,
            "provenance": {
                "source": entity.provenance.source,
                "timestamp": entity.provenance.timestamp.isoformat(),
                "agent": entity.provenance.agent,
                "model": entity.provenance.model,
                "search_query": entity.provenance.search_query,
            },
            "aliases": entity.aliases,
            "metadata": entity.metadata,
        }
        return await self._client.create("entity", data)

    async def create_relationship(self, rel: Relationship) -> Any:
        sql = """
            LET $from = (SELECT * FROM entity WHERE name = $source LIMIT 1);
            LET $to = (SELECT * FROM entity WHERE name = $target LIMIT 1);
            RELATE $from->relates_to->$to SET
                relation_type = $relation_type,
                confidence = $confidence,
                provenance = $provenance;
        """
        params = {
            "source": rel.source,
            "target": rel.target,
            "relation_type": rel.relation_type,
            "confidence": rel.confidence,
            "provenance": {
                "source": rel.provenance.source,
                "timestamp": rel.provenance.timestamp.isoformat(),
                "agent": rel.provenance.agent,
            },
        }
        return await self._client.query(sql, params)

    async def find_entity_by_name(self, name: str) -> list[Any]:
        return await self._client.query(
            "SELECT * FROM entity WHERE name = $name",
            {"name": name},
        )

    async def find_entities_by_type(self, entity_type: str) -> list[Any]:
        return await self._client.query(
            "SELECT * FROM entity WHERE entity_type = $type",
            {"type": entity_type},
        )

    async def find_entities_by_branch(self, branch: str) -> list[Any]:
        return await self._client.query(
            "SELECT * FROM entity WHERE branch = $branch",
            {"branch": branch},
        )

    async def get_entity_count(self) -> int:
        result = await self._client.query("SELECT count() FROM entity GROUP ALL")
        if result and len(result) > 0:
            return result[0].get("count", 0)
        return 0

    async def get_relationship_count(self) -> int:
        result = await self._client.query("SELECT count() FROM relates_to GROUP ALL")
        if result and len(result) > 0:
            return result[0].get("count", 0)
        return 0

    async def get_branch_coverage(self) -> dict[str, int]:
        result = await self._client.query(
            "SELECT branch, count() as cnt FROM entity GROUP BY branch"
        )
        return {r["branch"]: r["cnt"] for r in result if r.get("branch")}
