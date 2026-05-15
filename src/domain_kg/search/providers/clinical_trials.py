"""ClinicalTrials.gov v2 API provider."""

from __future__ import annotations

import httpx
import structlog

from domain_kg.search.models import SearchResultItem
from domain_kg.search.providers.base import _SSL_CTX, SearchProvider

logger = structlog.get_logger("domain_kg.search.providers.clinical_trials")

CT_BASE_URL = "https://clinicaltrials.gov/api/v2/studies"


class ClinicalTrialsProvider(SearchProvider):
    """Clinical trial search via ClinicalTrials.gov v2 API."""

    name = "clinical_trials"

    def __init__(self, rate_limit: float = 3.0) -> None:
        super().__init__(rate_limit)

    async def search(self, query: str, max_results: int = 10) -> list[SearchResultItem]:
        await self._throttle()

        async with httpx.AsyncClient(timeout=30.0, verify=_SSL_CTX) as client:
            resp = await client.get(
                CT_BASE_URL,
                params={
                    "query.term": query,
                    "pageSize": max_results,
                    "fields": "NCTId,BriefTitle,OverallStatus,Phase,LeadSponsorName,Condition,InterventionName,StartDate,BriefSummary",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        items = []
        for study in data.get("studies", []):
            protocol = study.get("protocolSection", {})
            id_module = protocol.get("identificationModule", {})
            status_module = protocol.get("statusModule", {})
            sponsor_module = protocol.get("sponsorCollaboratorsModule", {})
            design_module = protocol.get("designModule", {})
            conditions_module = protocol.get("conditionsModule", {})
            interventions_module = protocol.get("armsInterventionsModule", {})
            desc_module = protocol.get("descriptionModule", {})

            nct_id = id_module.get("nctId", "")
            title = id_module.get("briefTitle", "")
            status = status_module.get("overallStatus", "")
            phases = design_module.get("phases", [])
            sponsor = sponsor_module.get("leadSponsor", {}).get("name", "")
            conditions = conditions_module.get("conditions", [])
            brief_summary = desc_module.get("briefSummary", "")

            interventions = []
            for arm in interventions_module.get("interventions", []):
                interventions.append(arm.get("name", ""))

            items.append(
                SearchResultItem(
                    url=f"https://clinicaltrials.gov/study/{nct_id}",
                    title=title,
                    snippet=brief_summary[:500] if brief_summary else "",
                    content=brief_summary,
                    published_date=status_module.get("startDateStruct", {}).get("date", ""),
                    source_type="clinical",
                    provider=self.name,
                    metadata={
                        "nct_id": nct_id,
                        "status": status,
                        "phases": phases,
                        "sponsor": sponsor,
                        "conditions": conditions,
                        "interventions": interventions,
                    },
                )
            )

        logger.info("ct.search.complete", query=query[:60], results=len(items))
        return items
