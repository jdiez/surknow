"""Discover available Bedrock models and select best per family.

Probes the AI Gateway (or direct Bedrock) to find which Claude models
are accessible, then selects the latest/best from each family.

Usage:
    uv run python -m domain_kg.tools.discover_models          # Full discovery
    uv run python -m domain_kg.tools.discover_models --validate  # Validate current .env

Can be called programmatically at workflow start to validate config:
    from domain_kg.tools.discover_models import validate_config, get_available_models
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass

import boto3


@dataclass
class ModelInfo:
    model_id: str
    family: str  # opus, sonnet, haiku
    generation: float  # 4.7, 4.6, 4, 3.7, 3.5, 3
    available: bool = False


# All known Claude model IDs ranked by preference within each family (newest first)
KNOWN_MODELS = [
    # Opus
    ModelInfo("us.anthropic.claude-opus-4-20250514-v1:0", "opus", 4.0),
    ModelInfo("us.anthropic.claude-3-opus-20240229-v1:0", "opus", 3.0),
    ModelInfo("anthropic.claude-3-opus-20240229-v1:0", "opus", 3.0),
    # Sonnet
    ModelInfo("us.anthropic.claude-sonnet-4-6-20250514-v1:0", "sonnet", 4.6),
    ModelInfo("us.anthropic.claude-sonnet-4-20250514-v1:0", "sonnet", 4.0),
    ModelInfo("us.anthropic.claude-3-7-sonnet-20250219-v1:0", "sonnet", 3.7),
    ModelInfo("anthropic.claude-3-7-sonnet-20250219-v1:0", "sonnet", 3.7),
    ModelInfo("us.anthropic.claude-3-5-sonnet-20241022-v2:0", "sonnet", 3.52),
    ModelInfo("anthropic.claude-3-5-sonnet-20241022-v2:0", "sonnet", 3.52),
    ModelInfo("us.anthropic.claude-3-5-sonnet-20240620-v1:0", "sonnet", 3.5),
    ModelInfo("anthropic.claude-3-5-sonnet-20240620-v1:0", "sonnet", 3.5),
    ModelInfo("anthropic.claude-3-sonnet-20240229-v1:0", "sonnet", 3.0),
    ModelInfo("us.anthropic.claude-3-sonnet-20240229-v1:0", "sonnet", 3.0),
    # Haiku
    ModelInfo("us.anthropic.claude-haiku-4-5-20251001-v1:0", "haiku", 4.5),
    ModelInfo("us.anthropic.claude-3-5-haiku-20241022-v1:0", "haiku", 3.5),
    ModelInfo("anthropic.claude-3-5-haiku-20241022-v1:0", "haiku", 3.5),
    ModelInfo("anthropic.claude-3-haiku-20240307-v1:0", "haiku", 3.0),
    ModelInfo("us.anthropic.claude-3-haiku-20240307-v1:0", "haiku", 3.0),
]


def _get_runtime_client():
    """Get bedrock-runtime client configured for gateway or direct access."""
    gateway_url = os.environ.get("AI_GATEWAY_URL", "")
    gateway_key = os.environ.get("AI_GATEWAY_KEY", "")
    region = os.environ.get("AWS_REGION", os.environ.get("DKG_AWS_REGION", "us-east-1"))

    if gateway_url and gateway_key:
        os.environ["AWS_BEARER_TOKEN_BEDROCK"] = gateway_key
        return boto3.client(
            "bedrock-runtime",
            region_name=region,
            endpoint_url=f"{gateway_url}/bedrock",
            aws_access_key_id="gateway",
            aws_secret_access_key="gateway",
        )
    return boto3.client("bedrock-runtime", region_name=region)


def get_available_models() -> list[ModelInfo]:
    """Probe all known models and return those that are accessible."""
    client = _get_runtime_client()
    results = []

    for model in KNOWN_MODELS:
        try:
            client.converse(
                modelId=model.model_id,
                messages=[{"role": "user", "content": [{"text": "hi"}]}],
                inferenceConfig={"maxTokens": 1},
            )
            model.available = True
        except Exception:
            model.available = False
        results.append(model)

    return results


def select_latest_per_family(models: list[ModelInfo]) -> dict[str, str]:
    """From available models, pick the latest (highest generation) per family."""
    available = [m for m in models if m.available]
    best: dict[str, str] = {}

    for family in ["opus", "sonnet", "haiku"]:
        family_models = sorted(
            [m for m in available if m.family == family],
            key=lambda m: m.generation,
            reverse=True,
        )
        if family_models:
            best[family] = family_models[0].model_id

    return best


def get_defaults() -> dict[str, str]:
    """Discover models and return defaults for each pipeline role."""
    models = get_available_models()
    latest = select_latest_per_family(models)

    return {
        "researcher": latest.get("opus", latest.get("sonnet", "")),
        "worker": latest.get("sonnet", ""),
        "lightweight": latest.get("haiku", latest.get("sonnet", "")),
    }


def validate_config() -> tuple[bool, dict[str, bool]]:
    """Validate configured model IDs are accessible. Returns (all_ok, {model: status})."""
    from domain_kg.config import Settings

    settings = Settings()
    models_to_check = list({
        settings.researcher_model_id,
        settings.worker_model_id,
        settings.bedrock_model_id,
    })

    client = _get_runtime_client()
    results: dict[str, bool] = {}

    for model_id in models_to_check:
        try:
            client.converse(
                modelId=model_id,
                messages=[{"role": "user", "content": [{"text": "hi"}]}],
                inferenceConfig={"maxTokens": 1},
            )
            results[model_id] = True
        except Exception:
            results[model_id] = False

    return all(results.values()), results


def main():
    """CLI: discover models, show availability, suggest defaults."""
    validate_only = "--validate" in sys.argv

    if validate_only:
        print("Validating configured models...\n")
        ok, results = validate_config()
        for model_id, available in results.items():
            status = "OK" if available else "UNAVAILABLE"
            print(f"  [{status}] {model_id}")
        if ok:
            print("\nAll configured models are accessible.")
        else:
            print("\nERROR: Some models are not available!")
            sys.exit(1)
        return

    print("Discovering available Bedrock models...\n")
    models = get_available_models()

    print("AVAILABLE:")
    for m in models:
        if m.available:
            print(f"  {m.model_id:55s}  [{m.family} {m.generation}]")

    print("\nUNAVAILABLE:")
    for m in models:
        if not m.available:
            print(f"  {m.model_id:55s}  [{m.family} {m.generation}]")

    latest = select_latest_per_family(models)
    print("\n--- RECOMMENDED DEFAULTS (latest per family) ---")
    print(f"  Researcher (opus):    {latest.get('opus', 'N/A')}")
    print(f"  Worker (sonnet):      {latest.get('sonnet', 'N/A')}")
    print(f"  Lightweight (haiku):  {latest.get('haiku', 'N/A')}")

    print("\n--- .env settings ---")
    print(f"  DKG_RESEARCHER_MODEL_ID={latest.get('opus', latest.get('sonnet', ''))}")
    print(f"  DKG_WORKER_MODEL_ID={latest.get('sonnet', '')}")
    print(f"  DKG_BEDROCK_MODEL_ID={latest.get('sonnet', '')}")


if __name__ == "__main__":
    main()
