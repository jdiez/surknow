"""Tests for agent tool resolver."""

from domain_kg.agents.tools import ToolResolver
from domain_kg.models import ToolDefinition, ToolRegistry


def _make_registry() -> ToolRegistry:
    return ToolRegistry(
        generic=[
            ToolDefinition(name="web_search", type="web_search", priority=10),
            ToolDefinition(name="tavily", type="search", priority=5),
        ],
        field_specific={
            "immunology": [
                ToolDefinition(name="pubmed", type="web_search", domains=["immunology"], priority=8),
            ],
            "software": [
                ToolDefinition(name="github", type="web_search", domains=["software"], priority=7),
            ],
        },
    )


def test_tools_for_domain_generic() -> None:
    resolver = ToolResolver(_make_registry())
    tools = resolver.tools_for_domain("Mathematics")
    assert len(tools) == 2
    assert tools[0].name == "web_search"
    assert tools[1].name == "tavily"


def test_tools_for_domain_with_field_match() -> None:
    resolver = ToolResolver(_make_registry())
    tools = resolver.tools_for_domain("Cancer Immunology Research")
    assert len(tools) == 3
    names = [t.name for t in tools]
    assert "pubmed" in names
    assert tools[0].priority >= tools[1].priority


def test_tools_for_domain_no_match_returns_generic_only() -> None:
    resolver = ToolResolver(_make_registry())
    tools = resolver.tools_for_domain("Cooking")
    assert all(t.name in ("web_search", "tavily") for t in tools)


def test_tools_sorted_by_priority_descending() -> None:
    resolver = ToolResolver(_make_registry())
    tools = resolver.tools_for_domain("Immunology and Software Engineering")
    priorities = [t.priority for t in tools]
    assert priorities == sorted(priorities, reverse=True)
