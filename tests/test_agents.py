"""Tests for agent definitions."""

from unittest.mock import patch

from domain_kg.agents.definitions import (
    GatewayBedrock,
    _build_bedrock_model,
    bedrock_claude,
    branch_explorer,
    domain_analyst,
    entity_extractor,
    graph_builder,
    search_strategist,
    vocabulary_collector,
)
from domain_kg.models import (
    BranchTree,
    DomainContext,
    KGResult,
    SearchPlan,
    VocabularyIndex,
)


def test_all_agents_defined() -> None:
    agents = [
        domain_analyst,
        branch_explorer,
        vocabulary_collector,
        search_strategist,
        entity_extractor,
        graph_builder,
    ]
    assert len(agents) == 6
    for agent in agents:
        assert agent.model is not None


def test_agent_output_schemas() -> None:
    assert domain_analyst.output_schema == DomainContext
    assert branch_explorer.output_schema == BranchTree
    assert vocabulary_collector.output_schema == VocabularyIndex
    assert search_strategist.output_schema == SearchPlan
    assert graph_builder.output_schema == KGResult


def test_agent_names() -> None:
    assert domain_analyst.name == "DomainAnalyst"
    assert branch_explorer.name == "BranchExplorer"
    assert vocabulary_collector.name == "VocabularyCollector"
    assert search_strategist.name == "SearchStrategist"
    assert entity_extractor.name == "EntityExtractor"
    assert graph_builder.name == "GraphBuilder"


def test_gateway_bedrock_type() -> None:
    if hasattr(bedrock_claude, "endpoint_url") and bedrock_claude.endpoint_url:
        assert isinstance(bedrock_claude, GatewayBedrock)


def test_build_bedrock_model_without_gateway(monkeypatch) -> None:
    monkeypatch.setenv("AI_GATEWAY_URL", "")
    monkeypatch.setenv("AI_GATEWAY_KEY", "")
    monkeypatch.delenv("AI_GATEWAY_URL", raising=False)
    monkeypatch.delenv("AI_GATEWAY_KEY", raising=False)
    from agno.models.aws import AwsBedrock

    with patch("domain_kg.agents.definitions._settings") as mock_settings:
        mock_settings.ai_gateway_url = ""
        mock_settings.ai_gateway_key = ""
        mock_settings.bedrock_model_id = "us.anthropic.claude-sonnet-4-20250514-v1:0"
        mock_settings.aws_region = "us-east-1"
        model = _build_bedrock_model()
        assert isinstance(model, AwsBedrock)
