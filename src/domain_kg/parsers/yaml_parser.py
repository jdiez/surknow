"""YAML input parser for domain descriptions."""

from pathlib import Path

import yaml

from domain_kg.models import DomainInput, SeedEntity, SeedLink


def parse_yaml(path: Path) -> DomainInput:
    """Parse a YAML domain description file into DomainInput."""
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    entities: list[SeedEntity] = []
    for entry in data.get("entities", []):
        entities.append(
            SeedEntity(
                name=entry["name"],
                type=entry["type"],
                description=entry.get("description"),
            )
        )

    links: list[SeedLink] = []
    for entry in data.get("links", []):
        links.append(
            SeedLink(
                source=entry["source"],
                target=entry["target"],
                relation=entry["relation"],
            )
        )

    return DomainInput(
        domain=data["domain"],
        description=data["description"],
        entities=entities,
        links=links,
    )
