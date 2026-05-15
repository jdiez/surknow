"""Plain text input parser for domain descriptions."""

import re
from pathlib import Path

from domain_kg.models import DomainInput, SeedEntity, SeedLink


def _parse_entities(raw: str) -> list[SeedEntity]:
    """Parse entity entries in the format: Name (type)."""
    entities: list[SeedEntity] = []
    pattern = re.compile(r"([^,]+?)\s*\((\w+)\)")
    for match in pattern.finditer(raw):
        entities.append(
            SeedEntity(
                name=match.group(1).strip(),
                type=match.group(2).strip(),
            )
        )
    return entities


def _parse_links(raw: str) -> list[SeedLink]:
    """Parse link entries in the format: Source -> relation -> Target."""
    links: list[SeedLink] = []
    pattern = re.compile(r"([^,]+?)\s*->\s*([^,]+?)\s*->\s*([^,]+)")
    for match in pattern.finditer(raw):
        links.append(
            SeedLink(
                source=match.group(1).strip(),
                target=match.group(3).strip(),
                relation=match.group(2).strip(),
            )
        )
    return links


def parse_text(path: Path) -> DomainInput:
    """Parse a plain text domain description file into DomainInput."""
    content = path.read_text(encoding="utf-8")

    domain_match = re.search(r"^Domain:\s*(.+)$", content, re.MULTILINE)
    domain = domain_match.group(1).strip() if domain_match else path.stem.replace("_", " ").title()

    desc_match = re.search(r"^Description:\s*(.+)$", content, re.MULTILINE)
    description = desc_match.group(1).strip() if desc_match else ""

    entities: list[SeedEntity] = []
    entities_match = re.search(r"^Entities:\s*(.+)$", content, re.MULTILINE)
    if entities_match:
        entities = _parse_entities(entities_match.group(1))

    links: list[SeedLink] = []
    links_match = re.search(r"^Links:\s*(.+)$", content, re.MULTILINE)
    if links_match:
        links = _parse_links(links_match.group(1))

    return DomainInput(
        domain=domain,
        description=description,
        entities=entities,
        links=links,
    )
