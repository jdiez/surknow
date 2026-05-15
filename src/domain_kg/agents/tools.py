"""Tool registry and resolver for agent tool injection."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from domain_kg.config import Settings
from domain_kg.models import ToolDefinition, ToolRegistry

if TYPE_CHECKING:
    from agno.agent import Agent

logger = structlog.get_logger("domain_kg.agents.tools")


class ToolResolver:
    """Resolves which tools an agent should use based on domain context."""

    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry

    def tools_for_domain(self, domain: str) -> list[ToolDefinition]:
        """Get all applicable tools for a given domain, sorted by priority."""
        tools = list(self._registry.generic)
        for field_key, field_tools in self._registry.field_specific.items():
            if field_key.lower() in domain.lower():
                tools.extend(field_tools)
        return sorted(tools, key=lambda t: t.priority, reverse=True)


def _build_tavily_tool(api_key: str):
    """Build Tavily search tool for Agno agents."""
    try:
        from agno.tools.tavily import TavilyTools

        return TavilyTools(api_key=api_key)
    except ImportError:
        logger.warning("tool.tavily.unavailable", reason="tavily-python not installed")
        return None


async def configure_agent_tools(agent: Agent, domain: str, registry: ToolRegistry) -> None:
    """Inject tools from registry into agent based on domain context."""
    resolver = ToolResolver(registry)
    tools = resolver.tools_for_domain(domain)
    settings = Settings()

    for tool_def in tools:
        if tool_def.type == "mcp" and tool_def.uri:
            from agno.tools.mcp import MCPTools

            mcp_tools = MCPTools(url=tool_def.uri)
            await mcp_tools.initialize()
            agent.tools.append(mcp_tools)
            logger.info("tool.mcp.loaded", name=tool_def.name, uri=tool_def.uri)
        elif tool_def.type in ("web_search", "search"):
            if settings.search_api_key:
                tavily = _build_tavily_tool(settings.search_api_key)
                if tavily:
                    agent.tools.append(tavily)
                    logger.info("tool.tavily.loaded", name=tool_def.name)
            else:
                logger.warning("tool.search.no_api_key", name=tool_def.name)

    logger.info("agent.tools.configured", agent=agent.name, tool_count=len(tools))
