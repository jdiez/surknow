"""Pipeline configuration via environment variables."""

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Pipeline configuration loaded from environment variables with DKG_ prefix."""

    # AWS Bedrock (via AI Gateway) — read from AI_GATEWAY_* (no prefix)
    ai_gateway_key: str = Field(default="", alias="AI_GATEWAY_KEY")
    ai_gateway_url: str = Field(default="", alias="AI_GATEWAY_URL")

    # SurrealDB
    surreal_url: str = "ws://localhost:8787/rpc"
    surreal_namespace: str = "domain_kg"
    surreal_database: str = "default"
    surreal_user: str = "root"
    surreal_pass: str = "root"

    # AWS Bedrock
    aws_region: str = "us-east-1"
    bedrock_model_id: str = "us.anthropic.claude-sonnet-4-20250514-v1:0"

    # Agno
    agno_storage_url: str = "postgresql://localhost:5432/domain_kg"

    # Agent models
    researcher_model_id: str = "us.anthropic.claude-opus-4-20250514-v1:0"
    worker_model_id: str = "us.anthropic.claude-sonnet-4-6-20250514-v1:0"

    # Pipeline
    max_iterations: int = 3
    coverage_threshold: float = 0.8
    confidence_threshold: float = 0.7
    max_entities_per_branch: int = 50
    parallel_branches: int = 5

    # Team settings
    research_team_max_iterations: int = 15
    extraction_team_max_iterations: int = 20
    graph_team_max_iterations: int = 10
    max_tool_calls_per_agent: int = 30

    # Search providers
    search_provider: str = "tavily"
    search_api_key: str = ""
    exa_api_key: str = ""
    semantic_scholar_key: str = ""
    opencorporates_token: str = ""
    github_token: str = ""

    # Search execution
    search_max_results_per_query: int = 10
    search_rate_limit_per_second: float = 2.0
    search_concurrent_queries: int = 3

    model_config = {"env_file": ".env", "env_prefix": "DKG_", "populate_by_name": True}
