"""PubMed E-utilities provider for biomedical literature search."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import httpx
import structlog

from domain_kg.search.models import SearchResultItem
from domain_kg.search.providers.base import _SSL_CTX, SearchProvider

logger = structlog.get_logger("domain_kg.search.providers.pubmed")

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


class PubMedProvider(SearchProvider):
    """Biomedical literature search via PubMed E-utilities."""

    name = "pubmed"

    def __init__(self, api_key: str | None = None, rate_limit: float = 1.0) -> None:
        super().__init__(rate_limit)
        self._api_key = api_key

    async def search(self, query: str, max_results: int = 10) -> list[SearchResultItem]:
        await self._throttle()

        params: dict = {"db": "pubmed", "term": query, "retmax": max_results, "retmode": "json"}
        if self._api_key:
            params["api_key"] = self._api_key

        async with httpx.AsyncClient(timeout=30.0, verify=_SSL_CTX) as client:
            search_resp = await client.get(f"{EUTILS_BASE}/esearch.fcgi", params=params)
            search_resp.raise_for_status()
            search_data = search_resp.json()

            id_list = search_data.get("esearchresult", {}).get("idlist", [])
            if not id_list:
                return []

            await self._throttle()
            fetch_params: dict = {
                "db": "pubmed",
                "id": ",".join(id_list),
                "rettype": "abstract",
                "retmode": "xml",
            }
            if self._api_key:
                fetch_params["api_key"] = self._api_key

            fetch_resp = await client.get(f"{EUTILS_BASE}/efetch.fcgi", params=fetch_params)
            fetch_resp.raise_for_status()

        items = self._parse_xml(fetch_resp.text)
        logger.info("pubmed.search.complete", query=query[:60], results=len(items))
        return items

    def _parse_xml(self, xml_text: str) -> list[SearchResultItem]:
        items = []
        root = ET.fromstring(xml_text)  # noqa: S314 — PubMed is a trusted source

        for article in root.findall(".//PubmedArticle"):
            pmid_el = article.find(".//PMID")
            pmid = pmid_el.text if pmid_el is not None else ""

            title_el = article.find(".//ArticleTitle")
            title = title_el.text if title_el is not None else ""

            abstract_parts = article.findall(".//AbstractText")
            abstract = " ".join(
                (part.text or "") for part in abstract_parts
            )

            authors = []
            for author in article.findall(".//Author"):
                last = author.find("LastName")
                first = author.find("ForeName")
                if last is not None and last.text:
                    name = last.text
                    if first is not None and first.text:
                        name = f"{first.text} {name}"
                    authors.append(name)

            year_el = article.find(".//PubDate/Year")
            year = year_el.text if year_el is not None else ""

            items.append(
                SearchResultItem(
                    url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    title=title or "",
                    snippet=abstract[:500] if abstract else "",
                    content=abstract,
                    published_date=year,
                    source_type="academic",
                    provider=self.name,
                    metadata={
                        "pmid": pmid,
                        "authors": authors,
                    },
                )
            )

        return items
