"""Tests for configuration module."""

import os

from domain_kg.config import Settings


def test_settings_defaults() -> None:
    settings = Settings()
    assert settings.surreal_url == "ws://localhost:8000/rpc"
    assert settings.surreal_namespace == "domain_kg"
    assert settings.surreal_database == "default"
    assert settings.aws_region == "us-east-1"
    assert settings.max_iterations == 3
    assert settings.coverage_threshold == 0.8
    assert settings.confidence_threshold == 0.7
    assert settings.max_entities_per_branch == 50
    assert settings.parallel_branches == 5


def test_settings_env_prefix(monkeypatch) -> None:
    monkeypatch.setenv("DKG_MAX_ITERATIONS", "10")
    monkeypatch.setenv("DKG_COVERAGE_THRESHOLD", "0.95")
    settings = Settings()
    assert settings.max_iterations == 10
    assert settings.coverage_threshold == 0.95


def test_settings_gateway_alias(monkeypatch) -> None:
    monkeypatch.setenv("AI_GATEWAY_KEY", "test-key")
    monkeypatch.setenv("AI_GATEWAY_URL", "https://test-gateway.example.com")
    settings = Settings()
    assert settings.ai_gateway_key == "test-key"
    assert settings.ai_gateway_url == "https://test-gateway.example.com"


def test_settings_bedrock_model_id() -> None:
    settings = Settings()
    assert "anthropic" in settings.bedrock_model_id
    assert settings.bedrock_model_id.startswith("us.")
