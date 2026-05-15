"""OpenCorporates API provider for company registry data."""

from __future__ import annotations

import httpx
import structlog

from domain_kg.search.models import SearchResultItem
from domain_kg.search.providers.base import _SSL_CTX, SearchProvider

logger = structlog.get_logger("domain_kg.search.providers.opencorporates")

OC_BASE_URL = "https://api.opencorporates.com/v0.4"


class OpenCorporatesProvider(SearchProvider):
    """Company registry search via OpenCorporates API. Free tier available."""

    name = "opencorporates"

    def __init__(self, api_token: str | None = None, rate_limit: float = 1.0) -> None:
        super().__init__(rate_limit)
        self._api_token = api_token

    async def search(self, query: str, max_results: int = 10) -> list[SearchResultItem]:
        await self._throttle()

        params: dict = {
            "q": query,
            "per_page": max_results,
            "order": "score",
        }
        if self._api_token:
            params["api_token"] = self._api_token

        async with httpx.AsyncClient(timeout=30.0, verify=_SSL_CTX) as client:
            resp = await client.get(f"{OC_BASE_URL}/companies/search", params=params)
            resp.raise_for_status()
            data = resp.json()

        items = []
        companies = data.get("results", {}).get("companies", [])

        for entry in companies:
            company = entry.get("company", {})
            name = company.get("name", "")
            jurisdiction = company.get("jurisdiction_code", "")
            status = company.get("current_status", "")
            inc_date = company.get("incorporation_date", "")
            company_number = company.get("company_number", "")
            registry_url = company.get("registry_url", "")
            oc_url = company.get("opencorporates_url", "")

            snippet = f"{name} ({jurisdiction.upper()})"
            if status:
                snippet += f" — Status: {status}"
            if inc_date:
                snippet += f" — Incorporated: {inc_date}"

            items.append(
                SearchResultItem(
                    url=oc_url or registry_url or "",
                    title=name,
                    snippet=snippet,
                    content=None,
                    published_date=inc_date,
                    source_type="company",
                    provider=self.name,
                    metadata={
                        "jurisdiction": jurisdiction,
                        "status": status,
                        "incorporation_date": inc_date,
                        "company_number": company_number,
                        "registry_url": registry_url,
                    },
                )
            )

        logger.info("opencorporates.search.complete", query=query[:60], results=len(items))
        return items
