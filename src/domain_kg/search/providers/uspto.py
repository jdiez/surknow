"""USPTO PatentsView API provider for US patent search."""

from __future__ import annotations

import httpx
import structlog

from domain_kg.search.models import SearchResultItem
from domain_kg.search.providers.base import _SSL_CTX, SearchProvider

logger = structlog.get_logger("domain_kg.search.providers.uspto")

PATENTSVIEW_BASE = "https://api.patentsview.org/patents/query"


class USPTOProvider(SearchProvider):
    """US patent search via PatentsView API. Free, no auth required."""

    name = "uspto"

    def __init__(self, rate_limit: float = 2.0) -> None:
        super().__init__(rate_limit)

    async def search(self, query: str, max_results: int = 10) -> list[SearchResultItem]:
        await self._throttle()

        payload = {
            "q": {"_text_any": {"patent_abstract": query}},
            "f": [
                "patent_number",
                "patent_title",
                "patent_abstract",
                "patent_date",
                "assignee_organization",
                "inventor_first_name",
                "inventor_last_name",
                "cpc_group_id",
                "cpc_group_title",
            ],
            "o": {"page": 1, "per_page": max_results},
            "s": [{"patent_date": "desc"}],
        }

        async with httpx.AsyncClient(timeout=30.0, verify=_SSL_CTX) as client:
            resp = await client.post(
                PATENTSVIEW_BASE,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()

        items = []
        for patent in data.get("patents", []):
            patent_num = patent.get("patent_number", "")
            title = patent.get("patent_title", "")
            abstract = patent.get("patent_abstract", "") or ""

            assignees = []
            for a in patent.get("assignees", []):
                org = a.get("assignee_organization", "")
                if org:
                    assignees.append(org)

            inventors = []
            for inv in patent.get("inventors", []):
                first = inv.get("inventor_first_name", "")
                last = inv.get("inventor_last_name", "")
                if last:
                    inventors.append(f"{first} {last}".strip())

            cpcs = []
            for cpc in patent.get("cpcs", []):
                cpc_id = cpc.get("cpc_group_id", "")
                cpc_title = cpc.get("cpc_group_title", "")
                if cpc_id:
                    cpcs.append({"id": cpc_id, "title": cpc_title})

            items.append(
                SearchResultItem(
                    url=f"https://patents.google.com/patent/US{patent_num}",
                    title=title,
                    snippet=abstract[:500],
                    content=abstract,
                    published_date=patent.get("patent_date", ""),
                    source_type="patents",
                    provider=self.name,
                    metadata={
                        "patent_number": patent_num,
                        "assignees": assignees,
                        "inventors": inventors,
                        "cpc_classifications": cpcs,
                    },
                )
            )

        logger.info("uspto.search.complete", query=query[:60], results=len(items))
        return items
