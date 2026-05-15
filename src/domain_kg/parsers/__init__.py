"""Input parsers for domain descriptions."""

from pathlib import Path

from domain_kg.models import DomainInput
from domain_kg.parsers.csv_parser import parse_csv
from domain_kg.parsers.text_parser import parse_text
from domain_kg.parsers.yaml_parser import parse_yaml


async def parse_input(input_file: Path) -> DomainInput:
    """Parse input file based on extension."""
    suffix = input_file.suffix.lower()
    if suffix in (".yaml", ".yml"):
        return parse_yaml(input_file)
    elif suffix in (".csv", ".tsv"):
        return parse_csv(input_file)
    elif suffix in (".txt", ".md"):
        return parse_text(input_file)
    else:
        raise ValueError(f"Unsupported input format: {suffix}")
