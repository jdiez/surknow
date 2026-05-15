"""Routes search queries to appropriate providers based on source_type and config."""

from __future__ import annotations

import structlog

from domain_kg.config import Settings
from domain_kg.domain_config import DomainConfig
from domain_kg.models import SearchQuery
from domain_kg.search.providers.base import SearchProvider
from domain_kg.search.providers.clinical_trials import ClinicalTrialsProvider
from domain_kg.search.providers.exa import ExaProvider
from domain_kg.search.providers.opencorporates import OpenCorporatesProvider
from domain_kg.search.providers.pubmed import PubMedProvider
from domain_kg.search.providers.sec_edgar import SECEdgarProvider
from domain_kg.search.providers.semantic_scholar import SemanticScholarProvider
from domain_kg.search.providers.tavily import TavilyProvider
from domain_kg.search.providers.uspto import USPTOProvider

logger = structlog.get_logger("domain_kg.search.dispatcher")


class SearchDispatcher:
    """Resolves which providers handle a given query based on source_type and domain config."""

    def __init__(self, settings: Settings, domain_config: DomainConfig) -> None:
        self._settings = settings
        self._providers: dict[str, SearchProvider] = {}
        self._source_map: dict[str, list[str]] = {
            "academic": ["semantic_scholar"],
            "industry": ["tavily"],
            "patents": ["tavily"],
            "repos": ["tavily"],
        }
        self._init_providers(settings, domain_config)

    def _init_providers(self, settings: Settings, domain_config: DomainConfig) -> None:
        if settings.search_api_key:
            self._providers["tavily"] = TavilyProvider(
                api_key=settings.search_api_key,
                rate_limit=settings.search_rate_limit_per_second,
            )

        if settings.exa_api_key:
            self._providers["exa"] = ExaProvider(
                api_key=settings.exa_api_key,
                rate_limit=settings.search_rate_limit_per_second,
            )
            # Prefer Exa for industry/patents when available (better semantic relevance)
            self._source_map["industry"] = ["exa"]
            self._source_map["patents"] = ["exa"]

        self._providers["semantic_scholar"] = SemanticScholarProvider(
            api_key=settings.semantic_scholar_key or None,
            rate_limit=0.3,
        )

        # Free providers — always available
        self._providers["uspto"] = USPTOProvider(rate_limit=2.0)
        self._providers["opencorporates"] = OpenCorporatesProvider(
            api_token=settings.opencorporates_token or None,
            rate_limit=1.0,
        )
        self._providers["sec_edgar"] = SECEdgarProvider(rate_limit=5.0)

        # Wire patent/company source types to dedicated providers
        self._source_map["patents"] = [*self._source_map.get("patents", []), "uspto"]
        self._source_map.setdefault("company", []).extend(["opencorporates", "sec_edgar"])
        self._source_map.setdefault("industry", []).append("opencorporates")

        config_tools = domain_config.tools.get("field_specific", [])
        if isinstance(config_tools, list):
            for tool in config_tools:
                tool_name = tool.get("name", "")
                domains = tool.get("domains", [])
                rate = tool.get("rate_limit", 3)

                if tool_name == "pubmed" and "pubmed" not in self._providers:
                    self._providers["pubmed"] = PubMedProvider(rate_limit=rate)
                    for domain in domains:
                        self._source_map.setdefault(domain, []).append("pubmed")
                    if "academic" not in self._source_map.get("pubmed", []):
                        self._source_map.setdefault("academic", []).append("pubmed")

                elif tool_name == "clinical_trials" and "clinical_trials" not in self._providers:
                    self._providers["clinical_trials"] = ClinicalTrialsProvider(rate_limit=rate)
                    for domain in domains:
                        self._source_map.setdefault(domain, []).append("clinical_trials")
                    self._source_map.setdefault("industry", []).append("clinical_trials")

                elif tool_name == "semantic_scholar":
                    api_key = settings.semantic_scholar_key or None
                    self._providers["semantic_scholar"] = SemanticScholarProvider(
                        api_key=api_key, rate_limit=rate
                    )

        logger.info(
            "dispatcher.initialized",
            providers=list(self._providers.keys()),
            source_types=list(self._source_map.keys()),
        )

    def resolve_providers(self, query: SearchQuery) -> list[SearchProvider]:
        """Get the providers that should handle this query, ordered by priority."""
        provider_names = self._source_map.get(query.source_type, [])

        if not provider_names and "tavily" in self._providers:
            provider_names = ["tavily"]

        providers = []
        for name in provider_names:
            if name in self._providers:
                providers.append(self._providers[name])

        if not providers:
            logger.warning(
                "dispatcher.no_providers",
                source_type=query.source_type,
                query=query.query[:60],
            )

        return providers

    @property
    def available_providers(self) -> list[str]:
        return list(self._providers.keys())
