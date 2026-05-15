"""Tests for CSV/TSV parser."""

from pathlib import Path

from domain_kg.parsers.csv_parser import parse_csv


def test_parse_csv_entities(sample_csv: Path) -> None:
    result = parse_csv(sample_csv)
    assert result.domain
    assert len(result.entities) > 0


def test_parse_csv_with_links(tmp_path: Path) -> None:
    entities_file = tmp_path / "test_entities.csv"
    entities_file.write_text("name,type,description\nAlpha,concept,First entity\nBeta,method,Second entity\n")

    links_file = tmp_path / "test_links.csv"
    links_file.write_text("source,target,relation\nAlpha,Beta,uses\n")

    result = parse_csv(entities_file)
    assert len(result.entities) == 2
    assert result.entities[0].name == "Alpha"
    assert result.entities[0].type == "concept"
    assert len(result.links) == 1
    assert result.links[0].source == "Alpha"
    assert result.links[0].target == "Beta"


def test_parse_tsv(tmp_path: Path) -> None:
    tsv_file = tmp_path / "test_entities.tsv"
    tsv_file.write_text("name\ttype\tdescription\nGamma\ttool\tA tool\n")
    result = parse_csv(tsv_file)
    assert len(result.entities) == 1
    assert result.entities[0].type == "tool"
