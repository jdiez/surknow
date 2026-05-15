"""Search result models for the execution layer."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from domain_kg.models import SearchQuery


class SearchResultItem(BaseModel):
    """A single document/page returned by a search provider."""

    url: str
    title: str
    snippet: str
    content: str | None = None
    published_date: str | None = None
    source_type: str
    provider: str
    metadata: dict = {}


class SearchResult(BaseModel):
    """Results for a single SearchQuery execution."""

    query: SearchQuery
    items: list[SearchResultItem] = []
    executed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    skipped: bool = False
    error: str | None = None


class SearchExecutionReport(BaseModel):
    """Summary of an entire search plan execution."""

    total_queries: int
    executed: int
    skipped: int
    failed: int
    total_items: int
    results: list[SearchResult]
