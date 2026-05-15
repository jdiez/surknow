"""Tavily web search provider for industry, patents, and general queries."""

from __future__ import annotations

import structlog

from domain_kg.search.models import SearchResultItem
from domain_kg.search.providers.base import SearchProvider

logger = structlog.get_logger("domain_kg.search.providers.tavily")


class TavilyProvider(SearchProvider):
    """Web search via Tavily API."""

    name = "tavily"

    def __init__(self, api_key: str, rate_limit: float = 5.0) -> None:
        super().__init__(rate_limit)
        self._api_key = api_key

    async def search(self, query: str, max_results: int = 10) -> list[SearchResultItem]:
        await self._throttle()

        from tavily import AsyncTavilyClient

        client = AsyncTavilyClient(api_key=self._api_key)
        response = await client.search(
            query=query,
            max_results=max_results,
            include_raw_content=True,
            search_depth="advanced",
        )

        items = []
        for result in response.get("results", []):
            items.append(
                SearchResultItem(
                    url=result.get("url", ""),
                    title=result.get("title", ""),
                    snippet=result.get("content", ""),
                    content=result.get("raw_content"),
                    published_date=result.get("published_date"),
                    source_type="web",
                    provider=self.name,
                    metadata={"score": result.get("score", 0)},
                )
            )

        logger.info("tavily.search.complete", query=query[:60], results=len(items))
        return items
