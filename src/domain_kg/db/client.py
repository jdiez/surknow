"""SurrealDB async connection manager."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

import structlog
from surrealdb import Surreal

from domain_kg.config import Settings

logger = structlog.get_logger("domain_kg.db.client")


class SurrealClient:
    """Async wrapper around SurrealDB connection."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._db: Surreal | None = None

    async def connect(self) -> None:
        self._db = Surreal(self._settings.surreal_url)
        await self._db.connect()
        await self._db.signin({"user": self._settings.surreal_user, "pass": self._settings.surreal_pass})
        await self._db.use(self._settings.surreal_namespace, self._settings.surreal_database)
        logger.info("db.connected", url=self._settings.surreal_url)

    async def disconnect(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None
            logger.info("db.disconnected")

    async def query(self, sql: str, params: dict[str, Any] | None = None) -> list[Any]:
        if not self._db:
            raise RuntimeError("Not connected to SurrealDB")
        result = await self._db.query(sql, params or {})
        return result

    async def create(self, table: str, data: dict[str, Any]) -> Any:
        if not self._db:
            raise RuntimeError("Not connected to SurrealDB")
        return await self._db.create(table, data)

    async def select(self, resource: str) -> list[Any]:
        if not self._db:
            raise RuntimeError("Not connected to SurrealDB")
        return await self._db.select(resource)


@asynccontextmanager
async def get_client(settings: Settings | None = None):
    """Context manager for SurrealDB client lifecycle."""
    if settings is None:
        settings = Settings()
    client = SurrealClient(settings)
    await client.connect()
    try:
        yield client
    finally:
        await client.disconnect()
