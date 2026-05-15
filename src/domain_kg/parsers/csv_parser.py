"""CSV/TSV input parser for domain descriptions."""

import csv
from pathlib import Path

from domain_kg.models import DomainInput, SeedEntity, SeedLink


def _detect_delimiter(path: Path) -> str:
    """Return tab for .tsv files, comma otherwise."""
    if path.suffix.lower() == ".tsv":
        return "\t"
    return ","


def _domain_from_stem(stem: str) -> str:
    """Derive domain name from file stem."""
    cleaned = stem.replace("_entities", "").replace("_links", "")
    return cleaned.replace("_", " ").title()


def _read_entities(path: Path, delimiter: str) -> list[SeedEntity]:
    """Read entity rows from a CSV/TSV file."""
    entities: list[SeedEntity] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        fieldnames = [name.lower().strip() for name in (reader.fieldnames or [])]
        if "name" not in fieldnames or "type" not in fieldnames:
            return entities
        for row in reader:
            normalized = {k.lower().strip(): v.strip() for k, v in row.items() if v}
            entities.append(
                SeedEntity(
                    name=normalized["name"],
                    type=normalized["type"],
                    description=normalized.get("description"),
                )
            )
    return entities


def _read_links(path: Path, delimiter: str) -> list[SeedLink]:
    """Read link rows from a CSV/TSV file."""
    links: list[SeedLink] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        fieldnames = [name.lower().strip() for name in (reader.fieldnames or [])]
        if "source" not in fieldnames or "target" not in fieldnames:
            return links
        for row in reader:
            normalized = {k.lower().strip(): v.strip() for k, v in row.items() if v}
            links.append(
                SeedLink(
                    source=normalized["source"],
                    target=normalized["target"],
                    relation=normalized["relation"],
                )
            )
    return links


def parse_csv(path: Path) -> DomainInput:
    """Parse CSV/TSV domain description files into DomainInput."""
    delimiter = _detect_delimiter(path)
    stem = path.stem
    parent = path.parent

    entities_path = parent / f"{stem}_entities{path.suffix}"
    links_path = parent / f"{stem}_links{path.suffix}"

    entities: list[SeedEntity] = []
    links: list[SeedLink] = []

    if entities_path.exists() and links_path.exists():
        entities = _read_entities(entities_path, delimiter)
        links = _read_links(links_path, delimiter)
        domain = _domain_from_stem(stem)
    elif stem.endswith("_entities"):
        entities = _read_entities(path, delimiter)
        base_stem = stem.removesuffix("_entities")
        companion = parent / f"{base_stem}_links{path.suffix}"
        if companion.exists():
            links = _read_links(companion, delimiter)
        domain = _domain_from_stem(stem)
    elif stem.endswith("_links"):
        links = _read_links(path, delimiter)
        base_stem = stem.removesuffix("_links")
        companion = parent / f"{base_stem}_entities{path.suffix}"
        if companion.exists():
            entities = _read_entities(companion, delimiter)
        domain = _domain_from_stem(stem)
    else:
        entities = _read_entities(path, delimiter)
        links = _read_links(path, delimiter)
        if not entities and not links:
            links = _read_links(path, delimiter)
        domain = _domain_from_stem(stem)

    description = f"Domain knowledge graph for {domain}"

    return DomainInput(
        domain=domain,
        description=description,
        entities=entities,
        links=links,
    )
