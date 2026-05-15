"""Semantic Scholar API provider for academic paper search."""

from __future__ import annotations

import httpx
import structlog

from domain_kg.search.models import SearchResultItem
from domain_kg.search.providers.base import SearchProvider

logger = structlog.get_logger("domain_kg.search.providers.semantic_scholar")

S2_BASE_URL = "https://api.semanticscholar.org/graph/v1"
S2_FIELDS = "title,abstract,authors,year,citationCount,url,externalIds"


class SemanticScholarProvider(SearchProvider):
    """Academic paper search via Semantic Scholar Graph API."""

    name = "semantic_scholar"

    def __init__(self, api_key: str | None = None, rate_limit: float = 0.3) -> None:
        super().__init__(rate_limit)
        self._api_key = api_key

    async def search(self, query: str, max_results: int = 10) -> list[SearchResultItem]:
        await self._throttle()

        headers = {}
        if self._api_key:
            headers["x-api-key"] = self._api_key

        from domain_kg.search.providers.base import _SSL_CTX

        async with httpx.AsyncClient(timeout=30.0, verify=_SSL_CTX) as client:
            resp = await client.get(
                f"{S2_BASE_URL}/paper/search",
                params={"query": query, "limit": max_results, "fields": S2_FIELDS},
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()

        items = []
        for paper in data.get("data", []):
            authors = [a.get("name", "") for a in paper.get("authors", [])]
            doi = paper.get("externalIds", {}).get("DOI", "")
            url = paper.get("url", "")
            if doi and not url:
                url = f"https://doi.org/{doi}"

            items.append(
                SearchResultItem(
                    url=url,
                    title=paper.get("title", ""),
                    snippet=paper.get("abstract", "") or "",
                    content=paper.get("abstract"),
                    published_date=str(paper.get("year", "")),
                    source_type="academic",
                    provider=self.name,
                    metadata={
                        "authors": authors,
                        "citation_count": paper.get("citationCount", 0),
                        "doi": doi,
                        "paper_id": paper.get("paperId", ""),
                    },
                )
            )

        logger.info("s2.search.complete", query=query[:60], results=len(items))
        return items
