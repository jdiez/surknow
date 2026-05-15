"""Processing log for incremental run deduplication."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from hashlib import sha256

import structlog

from domain_kg.db.client import SurrealClient

logger = structlog.get_logger("domain_kg.agents.log")


class ProcessingLog:
    """Tracks what has been processed to enable incremental runs."""

    def __init__(self, db: SurrealClient) -> None:
        self._db = db

    @staticmethod
    def _hash_input(input_data: dict) -> str:
        return sha256(json.dumps(input_data, sort_keys=True).encode()).hexdigest()

    async def already_processed(self, stage: str, input_data: dict) -> bool:
        """Check if this exact input was already processed for this stage."""
        input_hash = self._hash_input(input_data)
        result = await self._db.query(
            "SELECT * FROM processing_log WHERE input_hash = $hash AND stage = $stage AND status = 'completed'",
            {"hash": input_hash, "stage": stage},
        )
        return len(result) > 0

    async def query_already_executed(self, query: str) -> bool:
        """Check if a specific search query was already run."""
        result = await self._db.query(
            "SELECT * FROM processing_log WHERE $query IN search_queries_executed",
            {"query": query},
        )
        return len(result) > 0

    async def source_already_ingested(self, url: str) -> bool:
        """Check if a source URL has already been processed."""
        result = await self._db.query(
            "SELECT * FROM source WHERE url = $url",
            {"url": url},
        )
        return len(result) > 0

    async def start_run(self, run_id: str, stage: str, input_data: dict) -> str:
        """Start a new processing run and return the input hash."""
        input_hash = self._hash_input(input_data)
        await self._db.create("processing_log", {
            "run_id": run_id,
            "stage": stage,
            "input_hash": input_hash,
            "status": "started",
            "started_at": datetime.now(tz=timezone.utc).isoformat(),
            "iteration": 0,
            "entities_added": 0,
            "relations_added": 0,
            "search_queries_executed": [],
            "sources_processed": [],
        })
        logger.info("run.started", run_id=run_id, stage=stage)
        return input_hash

    async def complete_run(
        self,
        run_id: str,
        stage: str,
        entities_added: int,
        relations_added: int,
        queries: list[str],
        sources: list[str],
    ) -> None:
        """Mark a processing run as completed."""
        await self._db.query(
            """UPDATE processing_log SET
                status = 'completed',
                completed_at = time::now(),
                entities_added = $entities,
                relations_added = $relations,
                search_queries_executed = $queries,
                sources_processed = $sources
            WHERE run_id = $run_id AND stage = $stage""",
            {
                "run_id": run_id,
                "stage": stage,
                "entities": entities_added,
                "relations": relations_added,
                "queries": queries,
                "sources": sources,
            },
        )
        logger.info(
            "run.completed",
            run_id=run_id,
            stage=stage,
            entities=entities_added,
            relations=relations_added,
        )

    async def fail_run(self, run_id: str, stage: str, error: str) -> None:
        """Mark a processing run as failed."""
        await self._db.query(
            """UPDATE processing_log SET
                status = 'failed',
                completed_at = time::now()
            WHERE run_id = $run_id AND stage = $stage""",
            {"run_id": run_id, "stage": stage},
        )
        logger.error("run.failed", run_id=run_id, stage=stage, error=error)
