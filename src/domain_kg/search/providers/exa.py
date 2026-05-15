"""Exa neural search provider for high-relevance semantic search."""

from __future__ import annotations

import httpx
import structlog

from domain_kg.search.models import SearchResultItem
from domain_kg.search.providers.base import _SSL_CTX, SearchProvider

logger = structlog.get_logger("domain_kg.search.providers.exa")

EXA_BASE_URL = "https://api.exa.ai"


class ExaProvider(SearchProvider):
    """Neural/semantic search via Exa API. Higher relevance than keyword search."""

    name = "exa"

    def __init__(self, api_key: str, rate_limit: float = 5.0) -> None:
        super().__init__(rate_limit)
        self._api_key = api_key

    async def search(self, query: str, max_results: int = 10) -> list[SearchResultItem]:
        await self._throttle()

        headers = {
            "x-api-key": self._api_key,
            "Content-Type": "application/json",
        }

        payload = {
            "query": query,
            "numResults": max_results,
            "type": "neural",
            "useAutoprompt": True,
            "contents": {
                "text": {"maxCharacters": 4000},
                "highlights": {"numSentences": 3},
            },
        }

        async with httpx.AsyncClient(timeout=30.0, verify=_SSL_CTX) as client:
            resp = await client.post(
                f"{EXA_BASE_URL}/search",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        items = []
        for result in data.get("results", []):
            highlights = result.get("highlights", [])
            snippet = " ".join(highlights) if highlights else result.get("text", "")[:500]

            items.append(
                SearchResultItem(
                    url=result.get("url", ""),
                    title=result.get("title", ""),
                    snippet=snippet,
                    content=result.get("text"),
                    published_date=result.get("publishedDate"),
                    source_type="web",
                    provider=self.name,
                    metadata={
                        "score": result.get("score", 0),
                        "author": result.get("author", ""),
                    },
                )
            )

        logger.info("exa.search.complete", query=query[:60], results=len(items))
        return items
