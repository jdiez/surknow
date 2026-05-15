"""Domain-specific configuration loader."""

from pathlib import Path

import yaml
from pydantic import BaseModel

from domain_kg.config import Settings
from domain_kg.models import ToolDefinition, ToolRegistry


class DomainConfig(BaseModel):
    domain: str
    description: str
    references: dict[str, list[dict]] = {}
    tools: dict = {}
    examples: dict = {}
    agent_config: dict = {}


def load_domain_config(config_path: Path) -> DomainConfig:
    with open(config_path) as f:
        data = yaml.safe_load(f)
    return DomainConfig(**data)


def build_tool_registry(domain_config: DomainConfig, settings: Settings) -> ToolRegistry:
    generic_tools = []
    field_specific_tools: dict[str, list[ToolDefinition]] = {}

    tools_config = domain_config.tools

    for tool_data in tools_config.get("generic", []):
        generic_tools.append(ToolDefinition(**tool_data))

    field_specific_raw = tools_config.get("field_specific", [])
    if isinstance(field_specific_raw, list):
        for tool_data in field_specific_raw:
            tool = ToolDefinition(**tool_data)
            for domain in tool.domains:
                field_specific_tools.setdefault(domain, []).append(tool)
    elif isinstance(field_specific_raw, dict):
        for field_name, field_tools in field_specific_raw.items():
            field_specific_tools[field_name] = [
                ToolDefinition(**td) for td in field_tools
            ]

    mcp_servers = [
        ToolDefinition(**server_data)
        for server_data in tools_config.get("mcp_servers", [])
    ]

    if settings.search_api_key and not any(
        t.name == settings.search_provider for t in generic_tools
    ):
        generic_tools.append(
            ToolDefinition(
                name=settings.search_provider,
                type="search",
                api_key_env="DKG_SEARCH_API_KEY",
                priority=0,
            )
        )

    return ToolRegistry(
        generic=generic_tools,
        field_specific=field_specific_tools,
        mcp_servers=mcp_servers,
    )


def build_reference_context(domain_config: DomainConfig) -> str:
    lines = [f"Domain: {domain_config.domain}", f"Description: {domain_config.description}", ""]

    if domain_config.references:
        lines.append("References:")
        for category, refs in domain_config.references.items():
            lines.append(f"  {category}:")
            for ref in refs:
                name = ref.get("name", "Unknown")
                url = ref.get("url", "")
                description = ref.get("description", "")
                line = f"    - {name}"
                if url:
                    line += f" ({url})"
                if description:
                    line += f": {description}"
                lines.append(line)
        lines.append("")

    return "\n".join(lines)
