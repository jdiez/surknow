"""Tests for Pydantic models."""

from domain_kg.models import (
    CoverageMetrics,
    DomainInput,
    Entity,
    EntityType,
    Provenance,
    SeedEntity,
    SeedLink,
)


def test_domain_input_minimal() -> None:
    di = DomainInput(domain="Test", description="A test domain")
    assert di.domain == "Test"
    assert di.entities == []
    assert di.links == []


def test_domain_input_with_seeds() -> None:
    di = DomainInput(
        domain="Test",
        description="A test domain",
        entities=[SeedEntity(name="X", type="concept")],
        links=[SeedLink(source="X", target="Y", relation="uses")],
    )
    assert len(di.entities) == 1
    assert len(di.links) == 1


def test_provenance_defaults() -> None:
    p = Provenance(source="test", agent="TestAgent", model="claude", confidence=0.9)
    assert p.iteration == 0
    assert p.search_query is None
    assert p.timestamp is not None


def test_entity_type_values() -> None:
    assert EntityType.person == "person"
    assert EntityType.drug == "drug"
    assert EntityType.custom == "custom"


def test_coverage_metrics_threshold() -> None:
    cm = CoverageMetrics(
        branches_covered=8,
        total_branches=10,
        coverage_pct=0.8,
        entities_total=100,
        relationships_total=50,
    )
    assert cm.meets_threshold(0.8) is True
    assert cm.meets_threshold(0.9) is False


def test_entity_creation() -> None:
    e = Entity(
        name="Test Entity",
        entity_type=EntityType.concept,
        provenance=Provenance(source="test", agent="TestAgent", model="claude", confidence=0.95),
    )
    assert e.name == "Test Entity"
    assert e.entity_type == EntityType.concept
    assert e.aliases == []
