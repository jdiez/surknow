"""Agno agent definitions for each pipeline stage."""

import os
from dataclasses import dataclass, field
from typing import Any, Optional

import boto3
from agno.agent import Agent
from agno.models.aws import AwsBedrock

from domain_kg.config import Settings
from domain_kg.models import (
    BranchTree,
    DomainContext,
    KGResult,
    SearchPlan,
    VocabularyIndex,
)

_settings = Settings()


@dataclass
class GatewayBedrock(AwsBedrock):
    """AwsBedrock subclass that injects endpoint_url for async client (AI Gateway)."""

    endpoint_url: Optional[str] = field(default=None)

    def get_async_client(self):
        if self.endpoint_url:
            import aioboto3

            if self.async_session is None:
                self.async_session = aioboto3.Session()

            return self.async_session.client(
                service_name="bedrock-runtime",
                region_name=self.aws_region,
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
            )
        return super().get_async_client()


def _build_bedrock_model() -> AwsBedrock:
    """Build AwsBedrock model configured for AI Gateway."""
    if _settings.ai_gateway_url and _settings.ai_gateway_key:
        os.environ["AWS_BEARER_TOKEN_BEDROCK"] = _settings.ai_gateway_key
        os.environ.setdefault("AWS_ACCESS_KEY_ID", "gateway")
        os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "gateway")
        os.environ.setdefault("AWS_REGION", _settings.aws_region)

        gateway_endpoint = f"{_settings.ai_gateway_url}/bedrock"
        client = boto3.client(
            "bedrock-runtime",
            region_name=_settings.aws_region,
            endpoint_url=gateway_endpoint,
            aws_access_key_id="gateway",
            aws_secret_access_key="gateway",
        )
        return GatewayBedrock(
            id=_settings.bedrock_model_id,
            client=client,
            endpoint_url=gateway_endpoint,
            aws_access_key_id="gateway",
            aws_secret_access_key="gateway",
            aws_region=_settings.aws_region,
        )
    return AwsBedrock(id=_settings.bedrock_model_id, aws_region=_settings.aws_region)


bedrock_claude = _build_bedrock_model()

domain_analyst = Agent(
    name="DomainAnalyst",
    model=bedrock_claude,
    description="Analyzes domain descriptions and establishes scope, boundaries, and initial schema.",
    instructions=[
        "Expand the domain description into comprehensive context.",
        "Classify seed entities into an initial type schema.",
        "Identify domain boundaries — what is IN scope vs OUT.",
        "Detect adjacent and overlapping fields.",
        "Self-critique: what obvious aspects of this domain am I missing?",
    ],
    output_schema=DomainContext,
    markdown=False,
)

branch_explorer = Agent(
    name="BranchExplorer",
    model=bedrock_claude,
    description="Decomposes domains into hierarchical branches via iterative deepening.",
    instructions=[
        "Decompose the domain into hierarchical sub-fields (branches).",
        "For each branch, assess depth and coverage potential.",
        "Self-critique: what branches am I missing? What would a domain expert add?",
        "Use web search to validate branch existence and discover new ones.",
        "Iterate until coverage threshold or max rounds reached.",
    ],
    output_schema=BranchTree,
    tools=[],
    markdown=False,
)

vocabulary_collector = Agent(
    name="VocabularyCollector",
    model=bedrock_claude,
    description="Gathers domain-specific terminology per branch.",
    instructions=[
        "Extract all domain-specific terms for the assigned branch.",
        "Search for additional terminology used in academic and industry sources.",
        "Normalize to canonical forms, track aliases.",
        "Deduplicate against already-known terms from processing log.",
    ],
    output_schema=VocabularyIndex,
    tools=[],
    markdown=False,
)

search_strategist = Agent(
    name="SearchStrategist",
    model=bedrock_claude,
    description="Plans targeted searches to maximize entity coverage.",
    instructions=[
        "Generate structured search queries per branch.",
        "Prioritize by coverage gap — least-covered branches first.",
        "Plan sources: academic, industry, repos, patents.",
        "Skip queries already executed (check processing log).",
        "Define expected entity types per search.",
    ],
    output_schema=SearchPlan,
    markdown=False,
)

entity_extractor = Agent(
    name="EntityExtractor",
    model=bedrock_claude,
    description="Extracts entities and relationships from search results with confidence scoring.",
    instructions=[
        "Execute searches from the plan using available tools.",
        "Extract entities: name, type, description, branch.",
        "Identify relationships between entities.",
        "Score confidence for each extraction (0.0-1.0).",
        "Track provenance: source URL, query, timestamp.",
        "Skip sources already ingested (check processing log).",
    ],
    tools=[],
    markdown=False,
)

graph_builder = Agent(
    name="GraphBuilder",
    model=bedrock_claude,
    description="Resolves entities, merges with existing graph, writes to SurrealDB.",
    instructions=[
        "Deduplicate entities via fuzzy matching + semantic verification.",
        "Merge new entities with seed entities from input file.",
        "Write nodes and RELATE edges to SurrealDB.",
        "Discover schema constraints from entity types — apply SCHEMAFULL.",
        "Generate coverage report.",
    ],
    output_schema=KGResult,
    markdown=False,
)
