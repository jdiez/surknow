"""CLI interface for domain-kg pipeline."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from domain_kg.config import Settings

app = typer.Typer(name="domain-kg", help="Agentic Domain Characterization Pipeline")
console = Console()


@app.command()
def run(
    input_file: Path = typer.Argument(..., help="Domain input file (YAML/CSV/text)"),
    config_file: Path | None = typer.Option(None, "--config", "-c", help="Domain config file"),
    max_iterations: int = typer.Option(3, "--max-iterations", "-n", help="Maximum iteration rounds"),
    coverage: float = typer.Option(0.8, "--coverage", help="Target coverage threshold"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Parse input and show plan without executing"),
) -> None:
    """Characterize a domain and build its knowledge graph."""
    from domain_kg.flows.main import characterize_domain
    from domain_kg.parsers import parse_input

    settings = Settings(max_iterations=max_iterations, coverage_threshold=coverage)

    if dry_run:
        domain_input = asyncio.run(parse_input(input_file))
        console.print(f"[bold]Domain:[/bold] {domain_input.domain}")
        console.print(f"[bold]Description:[/bold] {domain_input.description}")
        console.print(f"[bold]Seed entities:[/bold] {len(domain_input.entities)}")
        console.print(f"[bold]Seed links:[/bold] {len(domain_input.links)}")
        console.print(f"[bold]Max iterations:[/bold] {max_iterations}")
        console.print(f"[bold]Coverage target:[/bold] {coverage}")
        return

    console.print(f"[bold green]Starting domain characterization:[/bold green] {input_file}")
    result = asyncio.run(characterize_domain(input_file, settings))

    table = Table(title="Pipeline Results")
    table.add_column("Metric", style="bold")
    table.add_column("Value")
    table.add_row("Entities Created", str(result.entities_created))
    table.add_row("Relationships Created", str(result.relationships_created))
    table.add_row("Entities Merged", str(result.entities_merged))
    table.add_row("Coverage", f"{result.coverage_pct:.1%}")
    table.add_row("Branches", f"{result.branches_covered}/{result.total_branches}")
    table.add_row("Iterations Used", str(result.iterations_used))
    console.print(table)


@app.command()
def status(domain: str = typer.Argument(..., help="Domain name to check")) -> None:
    """Show current graph status and coverage metrics."""
    from domain_kg.db.client import get_client
    from domain_kg.db.queries import QueryHelper

    async def _status() -> None:
        settings = Settings()
        async with get_client(settings) as client:
            helper = QueryHelper(client)
            entity_count = await helper.get_entity_count()
            rel_count = await helper.get_relationship_count()
            branch_coverage = await helper.get_branch_coverage()

        console.print(f"[bold]Domain:[/bold] {domain}")
        console.print(f"[bold]Entities:[/bold] {entity_count}")
        console.print(f"[bold]Relationships:[/bold] {rel_count}")
        console.print(f"[bold]Branches:[/bold] {len(branch_coverage)}")

        if branch_coverage:
            table = Table(title="Branch Coverage")
            table.add_column("Branch", style="bold")
            table.add_column("Entities")
            for branch, count in sorted(branch_coverage.items(), key=lambda x: x[1], reverse=True):
                table.add_row(branch, str(count))
            console.print(table)

    asyncio.run(_status())


@app.command()
def export(
    domain: str = typer.Argument(..., help="Domain name to export"),
    format: str = typer.Option("json", "--format", "-f", help="Export format: json, csv"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output file path"),
) -> None:
    """Export the knowledge graph in various formats."""
    import json as json_lib

    from domain_kg.db.client import get_client
    from domain_kg.db.queries import QueryHelper

    async def _export() -> str:
        settings = Settings()
        async with get_client(settings) as client:
            helper = QueryHelper(client)
            entities = await client.select("entity")
            relations = await client.query("SELECT * FROM relates_to")

        if format == "json":
            data = {"domain": domain, "entities": entities, "relationships": relations}
            return json_lib.dumps(data, indent=2, default=str)
        elif format == "csv":
            lines = ["name,type,branch,confidence"]
            for e in entities:
                lines.append(f"{e.get('name','')},{e.get('entity_type','')},{e.get('branch','')},{e.get('confidence','')}")
            return "\n".join(lines)
        else:
            return f"Unsupported format: {format}"

    result = asyncio.run(_export())

    if output:
        output.write_text(result)
        console.print(f"[green]Exported to {output}[/green]")
    else:
        console.print(result)


if __name__ == "__main__":
    app()
