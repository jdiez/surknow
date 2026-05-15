"""Tests for input parsers."""

from pathlib import Path

from domain_kg.parsers.yaml_parser import parse_yaml


def test_parse_yaml(sample_yaml: Path) -> None:
    result = parse_yaml(sample_yaml)
    assert result.domain == "Test Domain"
    assert result.description == "A simple test domain for unit testing"
    assert len(result.entities) == 2
    assert result.entities[0].name == "Entity A"
    assert result.entities[0].type == "concept"
    assert len(result.links) == 1
    assert result.links[0].source == "Entity A"
    assert result.links[0].target == "Entity B"
    assert result.links[0].relation == "relates_to"


def test_parse_yaml_entities_have_descriptions(sample_yaml: Path) -> None:
    result = parse_yaml(sample_yaml)
    assert result.entities[0].description == "First test entity"
    assert result.entities[1].description is None
