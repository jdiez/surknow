"""Agno Team definitions for the domain characterization pipeline."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

import boto3
from agno.agent import Agent
from agno.models.aws import AwsBedrock
from agno.team import Team
from agno.team.mode import TeamMode

from domain_kg.agents.search_tools import (
    AcademicSearchToolkit,
    ClinicalTrialsToolkit,
    CompanySearchToolkit,
    PatentSearchToolkit,
    WebSearchToolkit,
)
from domain_kg.config import Settings
from domain_kg.models import GraphResult, ResearchBrief


@dataclass
class GatewayBedrock(AwsBedrock):
    """AwsBedrock subclass that injects endpoint_url for async client (AI Gateway)."""

    endpoint_url: str | None = field(default=None)

    def get_async_client(self):
        if self.endpoint_url:
            import aioboto3
            from botocore.config import Config

            if self.async_session is None:
                self.async_session = aioboto3.Session()

            boto_config = Config(read_timeout=300, connect_timeout=10, retries={"max_attempts": 2})

            return self.async_session.client(
                service_name="bedrock-runtime",
                region_name=self.aws_region,
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                config=boto_config,
            )
        return super().get_async_client()


def _build_model(settings: Settings, model_id: str) -> AwsBedrock:
    """Build AwsBedrock model configured for AI Gateway."""
    from botocore.config import Config

    boto_config = Config(read_timeout=300, connect_timeout=10, retries={"max_attempts": 2})

    if settings.ai_gateway_url and settings.ai_gateway_key:
        os.environ["AWS_BEARER_TOKEN_BEDROCK"] = settings.ai_gateway_key
        os.environ.setdefault("AWS_ACCESS_KEY_ID", "gateway")
        os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "gateway")
        os.environ.setdefault("AWS_REGION", settings.aws_region)

        gateway_endpoint = f"{settings.ai_gateway_url}/bedrock"
        client = boto3.client(
            "bedrock-runtime",
            region_name=settings.aws_region,
            endpoint_url=gateway_endpoint,
            aws_access_key_id="gateway",
            aws_secret_access_key="gateway",
            config=boto_config,
        )
        return GatewayBedrock(
            id=model_id,
            client=client,
            endpoint_url=gateway_endpoint,
            aws_access_key_id="gateway",
            aws_secret_access_key="gateway",
            aws_region=settings.aws_region,
        )
    return AwsBedrock(id=model_id, aws_region=settings.aws_region)


def build_research_team(settings: Settings, domain_prompt: str) -> Team:
    """Build the Research Team (Team 1) with search tools."""
    opus_model = _build_model(settings, settings.researcher_model_id)
    worker_model = _build_model(settings, settings.worker_model_id)

    web_researcher = Agent(
        name="WebResearcher",
        role="Web search specialist",
        model=worker_model,
        tools=[WebSearchToolkit(settings)],
        instructions=[
            "You search the web for industry information, companies, products, news, and market landscape.",
            "When given a research task, use search_web to find relevant information.",
            "Return structured findings: key entities found, their descriptions, and source URLs.",
            "Focus on finding companies, products, key people, and market dynamics.",
        ],
        tool_call_limit=settings.max_tool_calls_per_agent,
        markdown=False,
    )

    academic_researcher = Agent(
        name="AcademicResearcher",
        role="Academic and clinical research specialist",
        model=worker_model,
        tools=[
            AcademicSearchToolkit(settings),
            ClinicalTrialsToolkit(),
            PatentSearchToolkit(),
        ],
        instructions=[
            "You search academic literature, clinical trials, and patents.",
            "Use search_papers for scientific publications and reviews.",
            "Use search_trials for clinical trial data (phases, sponsors, conditions).",
            "Use search_patents for intellectual property and technology claims.",
            "Return structured findings: key papers, trials, technologies, and researchers.",
        ],
        tool_call_limit=settings.max_tool_calls_per_agent,
        markdown=False,
    )

    industry_analyst = Agent(
        name="IndustryAnalyst",
        role="Corporate and financial intelligence specialist",
        model=worker_model,
        tools=[CompanySearchToolkit()],
        instructions=[
            "You search SEC filings and corporate data for business intelligence.",
            "Use search_companies to find 10-K, 10-Q, 8-K, and S-1 filings.",
            "Identify corporate structure, partnerships, funding, and market positioning.",
            "Return structured findings: companies, their products, partnerships, and financial data.",
        ],
        tool_call_limit=settings.max_tool_calls_per_agent,
        markdown=False,
    )

    return Team(
        name="ResearchTeam",
        mode=TeamMode.coordinate,
        model=opus_model,
        members=[web_researcher, academic_researcher, industry_analyst],
        instructions=[
            "You are a research director. Your goal is to deeply understand the domain described below.",
            "",
            "YOUR TEAM:",
            "- WebResearcher: Searches the web. Ask for companies, products, news, market players.",
            "- AcademicResearcher: Searches papers, clinical trials, patents. Ask for scientific foundations.",
            "- IndustryAnalyst: Searches SEC filings. Ask for corporate/financial intelligence.",
            "",
            "PROCESS:",
            "1. Start broad: ask WebResearcher for the landscape overview",
            "2. Go deep: ask AcademicResearcher for the science, trials, key publications",
            "3. Fill gaps: ask IndustryAnalyst for corporate structure, partnerships, funding",
            "4. Synthesize: combine all findings into a coherent picture",
            "5. Identify what's missing → delegate more targeted searches",
            "6. Conclude when you can confidently describe the field structure",
            "",
            "ROOT ENTITY CRITERIA:",
            "- Referenced by many other entities (hub node in the knowledge graph)",
            "- A domain expert would list it in 'top 20 things to know about this field'",
            "- Represents a key company, technology, person, trial, concept, or product",
            "",
            "OUTPUT: Produce 15-30 root entities across ALL major branches of the domain.",
            "",
            "DOMAIN CONTEXT:",
            domain_prompt,
        ],
        output_schema=ResearchBrief,
        max_iterations=settings.research_team_max_iterations,
        share_member_interactions=True,
        markdown=False,
    )


def build_extraction_team(settings: Settings, ontology_prompt: str) -> Team:
    """Build the Extraction Team (Team 2) for entity/relationship extraction."""
    worker_model = _build_model(settings, settings.worker_model_id)

    entity_extractor = Agent(
        name="EntityExtractor",
        role="Entity extraction specialist",
        model=worker_model,
        instructions=[
            "You extract structured entities from documents.",
            "For each entity found, provide: name, type, description, confidence score.",
            "Only extract entities matching the allowed types in the ontology.",
            "Score confidence based on how clearly the entity is described in the source.",
            "Include aliases and alternative names when present.",
        ],
        markdown=False,
    )

    relationship_mapper = Agent(
        name="RelationshipMapper",
        role="Relationship identification specialist",
        model=worker_model,
        instructions=[
            "You identify relationships between entities.",
            "For each relationship: source entity, target entity, relation type, confidence.",
            "Only use relation types from the allowed ontology.",
            "Relationships must be explicitly supported by the source text.",
            "Score confidence based on how clearly the relationship is stated.",
        ],
        markdown=False,
    )

    qa_validator = Agent(
        name="QAValidator",
        role="Quality assurance and validation specialist",
        model=worker_model,
        tools=[WebSearchToolkit(settings)],
        instructions=[
            "You validate extracted entities and relationships for accuracy.",
            "Check: Are entity names correct? Are types accurate? Are relationships real?",
            "Flag any extraction that seems hallucinated or unsupported by the source.",
            "You may use web search to fact-check questionable extractions.",
            "Return a validated set with rejected items explained.",
        ],
        tool_call_limit=10,
        markdown=False,
    )

    return Team(
        name="ExtractionTeam",
        mode=TeamMode.coordinate,
        model=worker_model,
        members=[entity_extractor, relationship_mapper, qa_validator],
        instructions=[
            "You are an extraction director. Process search results to extract structured entities and relationships.",
            "",
            "YOUR TEAM:",
            "- EntityExtractor: Extracts entities with type, description, confidence",
            "- RelationshipMapper: Identifies relationships between entities",
            "- QAValidator: Validates extractions, flags hallucinations",
            "",
            "PROCESS:",
            "1. Delegate document content to EntityExtractor for entity extraction",
            "2. Pass extracted entities to RelationshipMapper for relationship identification",
            "3. Send both to QAValidator for quality checks",
            "4. Produce final validated entity and relationship lists",
            "",
            "ONTOLOGY CONSTRAINTS:",
            ontology_prompt,
        ],
        max_iterations=settings.extraction_team_max_iterations,
        share_member_interactions=True,
        markdown=False,
    )


def build_graph_team(settings: Settings) -> Team:
    """Build the Graph Team (Team 3) for deduplication, validation, and coverage."""
    worker_model = _build_model(settings, settings.worker_model_id)

    deduplicator = Agent(
        name="Deduplicator",
        role="Entity deduplication specialist",
        model=worker_model,
        instructions=[
            "You identify and merge duplicate entities.",
            "Two entities are duplicates if they refer to the same real-world thing.",
            "Check: same name with different casing, aliases, abbreviations vs full names.",
            "When merging, keep the most complete description and combine all aliases.",
            "Report which entities were merged and why.",
        ],
        markdown=False,
    )

    schema_enforcer = Agent(
        name="SchemaEnforcer",
        role="Ontology and schema validation specialist",
        model=worker_model,
        instructions=[
            "You validate that all entities and relationships conform to the ontology.",
            "Check: entity types are valid, relation types are valid, names are normalized.",
            "Reject entities with invalid types or insufficient confidence.",
            "Normalize entity names to canonical forms.",
            "Report any schema violations found.",
        ],
        markdown=False,
    )

    coverage_analyst = Agent(
        name="CoverageAnalyst",
        role="Knowledge graph coverage assessment specialist",
        model=worker_model,
        instructions=[
            "You assess how complete the knowledge graph is.",
            "For each branch/sub-area of the domain, estimate coverage (0-1).",
            "Identify gaps: which branches have few entities? Which entity types are underrepresented?",
            "Recommend specific areas that need more research in the next iteration.",
            "Produce a coverage report with per-branch metrics.",
        ],
        markdown=False,
    )

    return Team(
        name="GraphTeam",
        mode=TeamMode.coordinate,
        model=worker_model,
        members=[deduplicator, schema_enforcer, coverage_analyst],
        instructions=[
            "You are a graph architect. Build a clean knowledge graph from extracted entities.",
            "",
            "YOUR TEAM:",
            "- Deduplicator: Merges duplicate entities referring to the same real-world thing",
            "- SchemaEnforcer: Validates types, normalizes names, enforces ontology constraints",
            "- CoverageAnalyst: Assesses completeness, identifies gaps for next iteration",
            "",
            "PROCESS:",
            "1. Delegate to Deduplicator: identify and merge duplicates",
            "2. Delegate to SchemaEnforcer: validate all entities/relationships against ontology",
            "3. Delegate to CoverageAnalyst: assess what's well-covered vs what's missing",
            "4. Produce final deduplicated, validated entity set with coverage report",
        ],
        output_schema=GraphResult,
        max_iterations=settings.graph_team_max_iterations,
        share_member_interactions=True,
        markdown=False,
    )
