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

    # Pipeline
    max_iterations: int = 3
    coverage_threshold: float = 0.8
    confidence_threshold: float = 0.7
    max_entities_per_branch: int = 50
    parallel_branches: int = 5

    # Default search
    search_provider: str = "tavily"
    search_api_key: str = ""

    model_config = {"env_file": ".env", "env_prefix": "DKG_", "populate_by_name": True}
