"""Tests for CLI interface."""

from pathlib import Path

from typer.testing import CliRunner

from domain_kg.cli import app

runner = CliRunner()


def test_cli_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Agentic Domain Characterization Pipeline" in result.output


def test_cli_run_help() -> None:
    result = runner.invoke(app, ["run", "--help"])
    assert result.exit_code == 0
    assert "input-file" in result.output.lower() or "INPUT_FILE" in result.output


def test_cli_dry_run(tmp_path: Path) -> None:
    input_file = tmp_path / "test.yaml"
    input_file.write_text(
        """
domain: "CLI Test"
description: "Testing CLI dry run"
entities:
  - name: "Test"
    type: "concept"
links: []
"""
    )
    result = runner.invoke(app, ["run", str(input_file), "--dry-run"])
    assert result.exit_code == 0
    assert "CLI Test" in result.output
    assert "Seed entities" in result.output


def test_cli_status_help() -> None:
    result = runner.invoke(app, ["status", "--help"])
    assert result.exit_code == 0


def test_cli_export_help() -> None:
    result = runner.invoke(app, ["export", "--help"])
    assert result.exit_code == 0
    assert "format" in result.output.lower()
