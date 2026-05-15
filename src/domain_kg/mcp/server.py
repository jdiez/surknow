"""MCP server for domain knowledge graph search tools."""

from __future__ import annotations

import asyncio
import json
import logging

from fastmcp import FastMCP

from domain_kg.config import Settings
from domain_kg.search.providers.clinical_trials import ClinicalTrialsProvider
from domain_kg.search.providers.exa import ExaProvider
from domain_kg.search.providers.pubmed import PubMedProvider
from domain_kg.search.providers.sec_edgar import SECEdgarProvider
from domain_kg.search.providers.semantic_scholar import SemanticScholarProvider
from domain_kg.search.providers.tavily import TavilyProvider
from domain_kg.search.providers.uspto import USPTOProvider

logger = logging.getLogger("domain_kg.mcp")

mcp = FastMCP("domain-kg-search")

_settings = Settings()

# Initialize providers at module load
_providers: dict = {}


def _init_providers():
    global _providers
    if _providers:
        return

    if _settings.search_api_key:
        _providers["tavily"] = TavilyProvider(api_key=_settings.search_api_key)
    if _settings.exa_api_key:
        _providers["exa"] = ExaProvider(api_key=_settings.exa_api_key)

    _providers["semantic_scholar"] = SemanticScholarProvider(
        api_key=_settings.semantic_scholar_key or None
    )
    _providers["pubmed"] = PubMedProvider()
    _providers["clinical_trials"] = ClinicalTrialsProvider()
    _providers["uspto"] = USPTOProvider()
    _providers["sec_edgar"] = SECEdgarProvider()


_init_providers()


@mcp.tool()
async def search_academic(query: str, max_results: int = 10) -> str:
    """Search academic papers via Semantic Scholar and PubMed.

    Args:
        query: Search query for academic literature
        max_results: Maximum results per provider (default 10)

    Returns:
        JSON array of search results with title, url, snippet, metadata
    """
    results = []

    if "semantic_scholar" in _providers:
        try:
            items = await _providers["semantic_scholar"].search(query, max_results)
            results.extend([item.model_dump(mode="json") for item in items])
        except Exception as e:
            logger.debug("semantic_scholar failed: %s", e)

    if "pubmed" in _providers:
        try:
            items = await _providers["pubmed"].search(query, max_results)
            results.extend([item.model_dump(mode="json") for item in items])
        except Exception as e:
            logger.debug("pubmed failed: %s", e)

    return json.dumps(results, indent=2)


@mcp.tool()
async def search_web(query: str, max_results: int = 10, provider: str = "auto") -> str:
    """Search the web for industry, news, and general content.

    Uses Exa (neural search) if available, falls back to Tavily (keyword search).

    Args:
        query: Search query
        max_results: Maximum results (default 10)
        provider: "exa", "tavily", or "auto" (default: auto picks best available)

    Returns:
        JSON array of search results with title, url, content, metadata
    """
    chosen = (
        _providers.get("exa") or _providers.get("tavily")
        if provider == "auto"
        else _providers.get(provider)
    )

    if not chosen:
        return json.dumps({"error": f"No web search provider available (requested: {provider})"})

    items = await chosen.search(query, max_results)
    return json.dumps([item.model_dump(mode="json") for item in items], indent=2)


@mcp.tool()
async def search_patents(query: str, max_results: int = 10) -> str:
    """Search US patents via USPTO PatentsView API.

    Returns structured patent data including assignees, inventors, and CPC classifications.

    Args:
        query: Patent search query (searches abstracts)
        max_results: Maximum results (default 10)

    Returns:
        JSON array of patent results with title, url, assignees, inventors, classifications
    """
    if "uspto" not in _providers:
        return json.dumps({"error": "USPTO provider not available"})

    items = await _providers["uspto"].search(query, max_results)
    return json.dumps([item.model_dump(mode="json") for item in items], indent=2)


@mcp.tool()
async def search_clinical_trials(query: str, max_results: int = 10) -> str:
    """Search clinical trials via ClinicalTrials.gov v2 API.

    Returns structured trial data including NCT ID, status, phase, sponsor, conditions.

    Args:
        query: Clinical trial search query
        max_results: Maximum results (default 10)

    Returns:
        JSON array of trial results with nct_id, status, phase, sponsor, conditions
    """
    if "clinical_trials" not in _providers:
        return json.dumps({"error": "ClinicalTrials provider not available"})

    items = await _providers["clinical_trials"].search(query, max_results)
    return json.dumps([item.model_dump(mode="json") for item in items], indent=2)


@mcp.tool()
async def search_companies(query: str, max_results: int = 10) -> str:
    """Search public company filings via SEC EDGAR.

    Returns SEC filings (10-K, 10-Q, 8-K, S-1) matching the query.

    Args:
        query: Company or topic search query
        max_results: Maximum results (default 10)

    Returns:
        JSON array of filing results with entity_name, form_type, filing details
    """
    if "sec_edgar" not in _providers:
        return json.dumps({"error": "SEC EDGAR provider not available"})

    items = await _providers["sec_edgar"].search(query, max_results)
    return json.dumps([item.model_dump(mode="json") for item in items], indent=2)


@mcp.tool()
async def search_multi(
    query: str,
    source_types: str = "academic,web",
    max_results: int = 5,
) -> str:
    """Search across multiple sources simultaneously.

    Dispatches the query to multiple providers based on source_types.

    Args:
        query: Search query
        source_types: Comma-separated list of: academic, web, patents, clinical_trials, companies
        max_results: Maximum results per source type (default 5)

    Returns:
        JSON object with results grouped by source type
    """
    types = [t.strip() for t in source_types.split(",")]
    results: dict = {}

    tasks = []
    for source_type in types:
        if source_type == "academic":
            tasks.append(("academic", search_academic(query, max_results)))
        elif source_type == "web":
            tasks.append(("web", search_web(query, max_results)))
        elif source_type == "patents":
            tasks.append(("patents", search_patents(query, max_results)))
        elif source_type == "clinical_trials":
            tasks.append(("clinical_trials", search_clinical_trials(query, max_results)))
        elif source_type == "companies":
            tasks.append(("companies", search_companies(query, max_results)))

    gathered = await asyncio.gather(*[t[1] for t in tasks], return_exceptions=True)

    for (source_type, _), result in zip(tasks, gathered, strict=True):
        if isinstance(result, Exception):
            results[source_type] = {"error": str(result)}
        else:
            results[source_type] = json.loads(result)

    return json.dumps(results, indent=2)


def run():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    run()
