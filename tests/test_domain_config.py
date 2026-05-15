"""Tests for domain configuration loader."""

from pathlib import Path

import pytest

from domain_kg.config import Settings
from domain_kg.domain_config import (
    DomainConfig,
    build_reference_context,
    build_tool_registry,
    load_domain_config,
)
from domain_kg.models import ToolRegistry


@pytest.fixture
def sample_config(tmp_path: Path) -> Path:
    config = tmp_path / "test_domain.yaml"
    config.write_text(
        """
domain: "Test Domain"
description: "A test domain"
references:
  academic:
    - name: "Paper 1"
      url: "https://example.com/paper1"
      description: "A test paper"
tools:
  generic:
    - name: "web_search"
      type: "web_search"
      priority: 10
  field_specific:
    - name: "pubmed"
      type: "web_search"
      domains: ["biology", "medicine"]
      priority: 5
"""
    )
    return config


def test_load_domain_config(sample_config: Path) -> None:
    config = load_domain_config(sample_config)
    assert config.domain == "Test Domain"
    assert config.description == "A test domain"
    assert "academic" in config.references
    assert len(config.references["academic"]) == 1


def test_build_tool_registry(sample_config: Path) -> None:
    config = load_domain_config(sample_config)
    settings = Settings()
    registry = build_tool_registry(config, settings)
    assert isinstance(registry, ToolRegistry)
    assert len(registry.generic) >= 1
    assert registry.generic[0].name == "web_search"


def test_build_tool_registry_field_specific(sample_config: Path) -> None:
    config = load_domain_config(sample_config)
    settings = Settings()
    registry = build_tool_registry(config, settings)
    assert "biology" in registry.field_specific
    assert registry.field_specific["biology"][0].name == "pubmed"


def test_build_reference_context(sample_config: Path) -> None:
    config = load_domain_config(sample_config)
    context = build_reference_context(config)
    assert "Test Domain" in context
    assert "Paper 1" in context
    assert "https://example.com/paper1" in context


def test_build_tool_registry_adds_search_provider() -> None:
    config = DomainConfig(domain="Test", description="Test")
    settings = Settings(search_api_key="test-key", search_provider="tavily")
    registry = build_tool_registry(config, settings)
    names = [t.name for t in registry.generic]
    assert "tavily" in names
