"""Agno Toolkit wrappers for search providers."""

from __future__ import annotations

import json
import logging

from agno.tools import Toolkit

from domain_kg.config import Settings
from domain_kg.search.providers.clinical_trials import ClinicalTrialsProvider
from domain_kg.search.providers.exa import ExaProvider
from domain_kg.search.providers.pubmed import PubMedProvider
from domain_kg.search.providers.sec_edgar import SECEdgarProvider
from domain_kg.search.providers.semantic_scholar import SemanticScholarProvider
from domain_kg.search.providers.tavily import TavilyProvider
from domain_kg.search.providers.uspto import USPTOProvider

logger = logging.getLogger("domain_kg.agents.search_tools")


class WebSearchToolkit(Toolkit):
    def __init__(self, settings: Settings):
        super().__init__(name="web_search")
        self._exa = ExaProvider(api_key=settings.exa_api_key) if settings.exa_api_key else None
        self._tavily = (
            TavilyProvider(api_key=settings.search_api_key) if settings.search_api_key else None
        )
        self.register(self.search_web)

    async def search_web(self, query: str, max_results: int = 10) -> str:
        """Search the web for companies, products, news, and general information. Returns JSON array of results with title, url, and content."""
        provider = self._exa or self._tavily
        if not provider:
            return json.dumps({"error": "No web search provider configured"})
        items = await provider.search(query, max_results)
        return json.dumps([item.model_dump(mode="json") for item in items], default=str)


class AcademicSearchToolkit(Toolkit):
    def __init__(self, settings: Settings):
        super().__init__(name="academic_search")
        self._s2 = SemanticScholarProvider(api_key=settings.semantic_scholar_key or None)
        self._pubmed = PubMedProvider()
        self.register(self.search_papers)

    async def search_papers(self, query: str, max_results: int = 10) -> str:
        """Search academic papers via Semantic Scholar and PubMed. Returns JSON array with title, authors, abstract, url."""
        results = []
        for provider in [self._s2, self._pubmed]:
            try:
                items = await provider.search(query, max_results // 2)
                results.extend([item.model_dump(mode="json") for item in items])
            except Exception as e:
                logger.debug("academic search provider failed: %s", e)
                continue
        return json.dumps(results, default=str)


class ClinicalTrialsToolkit(Toolkit):
    def __init__(self):
        super().__init__(name="clinical_trials_search")
        self._provider = ClinicalTrialsProvider()
        self.register(self.search_trials)

    async def search_trials(self, query: str, max_results: int = 10) -> str:
        """Search clinical trials on ClinicalTrials.gov. Returns JSON with NCT ID, status, phase, sponsor, conditions."""
        items = await self._provider.search(query, max_results)
        return json.dumps([item.model_dump(mode="json") for item in items], default=str)


class PatentSearchToolkit(Toolkit):
    def __init__(self):
        super().__init__(name="patent_search")
        self._provider = USPTOProvider()
        self.register(self.search_patents)

    async def search_patents(self, query: str, max_results: int = 10) -> str:
        """Search US patents via USPTO. Returns JSON with title, assignees, inventors, classifications."""
        items = await self._provider.search(query, max_results)
        return json.dumps([item.model_dump(mode="json") for item in items], default=str)


class CompanySearchToolkit(Toolkit):
    def __init__(self):
        super().__init__(name="company_search")
        self._provider = SECEdgarProvider()
        self.register(self.search_companies)

    async def search_companies(self, query: str, max_results: int = 10) -> str:
        """Search SEC EDGAR for company filings (10-K, 10-Q, 8-K). Returns JSON with company name, form type, filing details."""
        items = await self._provider.search(query, max_results)
        return json.dumps([item.model_dump(mode="json") for item in items], default=str)
