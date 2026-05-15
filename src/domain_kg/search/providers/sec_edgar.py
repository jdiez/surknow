"""SEC EDGAR full-text search provider for public company filings."""

from __future__ import annotations

import httpx
import structlog

from domain_kg.search.models import SearchResultItem
from domain_kg.search.providers.base import _SSL_CTX, SearchProvider

logger = structlog.get_logger("domain_kg.search.providers.sec_edgar")

EFTS_BASE = "https://efts.sec.gov/LATEST/search-index"


class SECEdgarProvider(SearchProvider):
    """Public company filing search via SEC EDGAR full-text search. Free, no auth."""

    name = "sec_edgar"

    def __init__(self, rate_limit: float = 5.0) -> None:
        super().__init__(rate_limit)

    async def search(self, query: str, max_results: int = 10) -> list[SearchResultItem]:
        await self._throttle()

        params = {
            "q": query,
            "dateRange": "custom",
            "startdt": "2020-01-01",
            "forms": "10-K,10-Q,8-K,S-1",
            "hits.hits.total": max_results,
        }

        headers = {
            "User-Agent": "SurknowResearch/1.0 (research@surknow.dev)",
            "Accept": "application/json",
        }

        async with httpx.AsyncClient(timeout=30.0, verify=_SSL_CTX) as client:
            resp = await client.get(
                "https://efts.sec.gov/LATEST/search-index",
                params=params,
                headers=headers,
            )
            if resp.status_code != 200:
                # Fall back to the simpler full-text search endpoint
                resp = await client.get(
                    "https://efts.sec.gov/LATEST/search-index",
                    params={"q": query, "forms": "10-K,10-Q,8-K", "from": 0, "size": max_results},
                    headers=headers,
                )
                if resp.status_code != 200:
                    logger.warning("sec_edgar.search.failed", status=resp.status_code)
                    return []

            data = resp.json()

        items = []
        hits = data.get("hits", {}).get("hits", [])

        for hit in hits[:max_results]:
            source = hit.get("_source", {})
            filing_id = source.get("file_num", "")
            entity_name = source.get("entity_name", "")
            form_type = source.get("form_type", "")
            filed_date = source.get("file_date", "")
            description = source.get("display_names", [""])[0] if source.get("display_names") else ""

            accession = source.get("accession_no", "").replace("-", "")
            url = ""
            if accession:
                url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&accession={accession}"

            snippet = f"{entity_name} — {form_type}"
            if filed_date:
                snippet += f" (filed {filed_date})"
            if description:
                snippet += f": {description}"

            items.append(
                SearchResultItem(
                    url=url,
                    title=f"{entity_name} — {form_type}",
                    snippet=snippet,
                    content=description,
                    published_date=filed_date,
                    source_type="company",
                    provider=self.name,
                    metadata={
                        "entity_name": entity_name,
                        "form_type": form_type,
                        "filing_id": filing_id,
                        "accession_number": source.get("accession_no", ""),
                    },
                )
            )

        logger.info("sec_edgar.search.complete", query=query[:60], results=len(items))
        return items
