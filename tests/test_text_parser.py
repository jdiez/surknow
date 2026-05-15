"""Tests for plain text parser."""

from pathlib import Path

from domain_kg.parsers.text_parser import parse_text


def test_parse_text_full(tmp_path: Path) -> None:
    text_file = tmp_path / "domain.txt"
    text_file.write_text(
        "Domain: Machine Learning\n"
        "Description: Study of algorithms that improve through experience\n"
        "Entities: Neural Network (method), PyTorch (tool), Transformer (concept)\n"
        "Links: Neural Network -> implements -> Transformer, PyTorch -> trains -> Neural Network\n"
    )
    result = parse_text(text_file)
    assert result.domain == "Machine Learning"
    assert result.description == "Study of algorithms that improve through experience"
    assert len(result.entities) == 3
    assert result.entities[0].name == "Neural Network"
    assert result.entities[0].type == "method"
    assert len(result.links) == 2
    assert result.links[0].source == "Neural Network"
    assert result.links[0].target == "Transformer"
    assert result.links[0].relation == "implements"


def test_parse_text_minimal(tmp_path: Path) -> None:
    text_file = tmp_path / "simple_domain.txt"
    text_file.write_text("Domain: Physics\nDescription: Study of matter and energy\n")
    result = parse_text(text_file)
    assert result.domain == "Physics"
    assert result.entities == []
    assert result.links == []


def test_parse_text_no_domain_line(tmp_path: Path) -> None:
    text_file = tmp_path / "no_domain.txt"
    text_file.write_text("Just some text about chemistry.\n")
    result = parse_text(text_file)
    assert result.domain == "No Domain"
