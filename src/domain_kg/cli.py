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
    from domain_kg.domain_config import load_domain_config
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

    domain_config = None
    if config_file and config_file.exists():
        domain_config = load_domain_config(config_file)

    console.print(f"[bold green]Starting domain characterization:[/bold green] {input_file}")
    result = asyncio.run(
        characterize_domain(
            input_file,
            settings=settings,
            domain_config=domain_config,
            config_path=config_file,
            dry_run=dry_run,
        )
    )

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
    format: str = typer.Option("json", "--format", "-f", help="Export format: json, csv, text"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output file or directory path"),
) -> None:
    """Export the knowledge graph in various formats."""
    import json as json_lib

    from domain_kg.db.client import get_client

    async def _export() -> str:
        settings = Settings()
        async with get_client(settings) as client:
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
        elif format == "text":
            return _format_text_export(domain, entities, relations)
        else:
            return f"Unsupported format: {format}"

    result = asyncio.run(_export())

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(result)
        console.print(f"[green]Exported to {output}[/green]")
    else:
        console.print(result)


@app.command()
def characterize(
    config_file: Path = typer.Argument(..., help="Domain config file (YAML)"),
    output_dir: Path = typer.Option(Path("output"), "--output", "-o", help="Output directory"),
    max_iterations: int = typer.Option(3, "--max-iterations", "-n", help="Maximum pipeline iterations"),
    coverage: float = typer.Option(0.8, "--coverage", help="Target coverage threshold"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Run research team only, don't execute searches"),
) -> None:
    """Run the agentic team pipeline: Research → Extraction → Graph.

    Uses Agno Teams with specialized agents at each stage.
    Output is saved as YAML/JSON in the output directory.
    """
    from domain_kg.domain_config import load_domain_config
    from domain_kg.flows.main import characterize_domain

    settings = Settings(max_iterations=max_iterations, coverage_threshold=coverage)

    if not config_file.exists():
        console.print(f"[red]Config file not found: {config_file}[/red]")
        raise typer.Exit(1)

    domain_config = load_domain_config(config_file)
    console.print(f"[bold green]Starting agentic pipeline:[/bold green] {domain_config.domain}")
    console.print("  Teams: Research → Extraction → Graph")
    console.print(f"  Max iterations: {max_iterations}, Coverage target: {coverage}")
    if dry_run:
        console.print("  [yellow]DRY RUN: research only, no search execution[/yellow]")

    result = asyncio.run(
        characterize_domain(
            settings=settings,
            domain_config=domain_config,
            config_path=config_file,
            output_dir=output_dir,
            dry_run=dry_run,
        )
    )

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
def explore(
    input_file: Path = typer.Argument(..., help="Domain input file (YAML)"),
    output_dir: Path = typer.Option(Path("output"), "--output", "-o", help="Output directory"),
    stage: int = typer.Option(1, "--stage", "-s", help="Run up to this stage (1-3)"),
) -> None:
    """Run SDK-powered exploration (web-grounded stages 1-3).

    Uses Claude Code SDK agents with real web search for domain exploration.
    Results are saved as JSON (resumable) and text (human-readable).
    """
    import json as json_lib

    from domain_kg.flows.understand import understand_domain
    from domain_kg.parsers import parse_input

    output_dir.mkdir(parents=True, exist_ok=True)
    state_dir = output_dir / ".state"
    state_dir.mkdir(exist_ok=True)

    async def _run():
        domain_input = await parse_input(input_file)

        # Stage 1: Understand (SDK)
        cached = state_dir / "understand_sdk.json"
        if cached.exists():
            from domain_kg.models import DomainContext
            context = DomainContext(**json_lib.loads(cached.read_text()))
            console.print("[dim]Stage 1 (understand/SDK): resumed from cache[/dim]")
        else:
            context = await understand_domain(domain_input, use_sdk=True)
            cached.write_text(json_lib.dumps(context.model_dump(), indent=2, default=str))
            console.print("[green]Stage 1 (understand/SDK): completed[/green]")

        slug = context.domain.lower().replace(" ", "_")
        (output_dir / f"{slug}_understanding.txt").write_text(
            f"Domain: {context.domain}\n"
            f"Description: {context.description}\n\n"
            f"Entity Types:\n" + "\n".join(f"  - {t}" for t in context.initial_entity_types) + "\n\n"
            f"Relation Types:\n" + "\n".join(f"  - {r}" for r in context.initial_relation_types) + "\n\n"
            f"Boundaries:\n" + "\n".join(f"  {b}" for b in context.boundaries) + "\n\n"
            f"Adjacent Fields:\n" + "\n".join(f"  - {f}" for f in context.adjacent_fields) + "\n"
        )

        if stage < 2:
            return context

        # Stage 2: Discover Branches (SDK)
        from domain_kg.flows.discover import discover_branches
        from domain_kg.models import BranchTree

        cached_branches = state_dir / "branches_sdk.json"
        if cached_branches.exists():
            tree = BranchTree(**json_lib.loads(cached_branches.read_text()))
            console.print("[dim]Stage 2 (branches/SDK): resumed from cache[/dim]")
        else:
            tree = await discover_branches(context, iteration=1, use_sdk=True)
            cached_branches.write_text(json_lib.dumps(tree.model_dump(), indent=2, default=str))
            console.print("[green]Stage 2 (branches/SDK): completed[/green]")

        (output_dir / f"{slug}_branches.txt").write_text(
            f"Domain: {context.domain}\n"
            f"Branches: {len(tree.branches)}\n\n"
            + "\n".join(
                f"{'  ' * b.depth}[{b.confidence:.0%}] {b.name}\n"
                f"{'  ' * b.depth}  {b.description}"
                for b in tree.branches
            )
            + "\n"
        )

        return context

    console.print(f"[bold green]SDK Exploration:[/bold green] {input_file}")
    asyncio.run(_run())
    console.print(f"[green]Output written to {output_dir}/[/green]")


def _format_text_export(domain: str, entities: list, relations: list) -> str:
    """Format entities and relationships as readable text."""
    lines = [f"Domain: {domain}", f"Entities: {len(entities)}", f"Relationships: {len(relations)}", ""]

    by_branch: dict[str, list] = {}
    for e in entities:
        branch = e.get("branch", "Uncategorized") or "Uncategorized"
        by_branch.setdefault(branch, []).append(e)

    for branch in sorted(by_branch.keys()):
        lines.append(f"=== {branch} ({len(by_branch[branch])} entities) ===")
        for e in sorted(by_branch[branch], key=lambda x: x.get("name", "")):
            etype = e.get("entity_type", "")
            name = e.get("name", "")
            desc = e.get("description", "") or ""
            conf = e.get("confidence", 0)
            lines.append(f"  [{etype}] {name} (conf={conf:.2f})")
            if desc:
                lines.append(f"    {desc}")
        lines.append("")

    if relations:
        lines.append("=== Relationships ===")
        for r in relations:
            src = r.get("in", {})
            tgt = r.get("out", {})
            src_name = src.get("name", str(src)) if isinstance(src, dict) else str(src)
            tgt_name = tgt.get("name", str(tgt)) if isinstance(tgt, dict) else str(tgt)
            rel_type = r.get("relation_type", "relates_to")
            lines.append(f"  {src_name} --[{rel_type}]--> {tgt_name}")

    return "\n".join(lines) + "\n"


@app.command()
def models(
    validate: bool = typer.Option(False, "--validate", help="Only validate current config"),
) -> None:
    """Discover available Bedrock models and show recommended defaults."""
    from domain_kg.tools.discover_models import (
        get_available_models,
        select_latest_per_family,
        validate_config,
    )

    if validate:
        console.print("[bold]Validating configured models...[/bold]")
        ok, results = validate_config()
        for model_id, available in results.items():
            status = "[green]OK[/green]" if available else "[red]UNAVAILABLE[/red]"
            console.print(f"  {status} {model_id}")
        if not ok:
            console.print("\n[red]Some models are not available![/red]")
            raise typer.Exit(1)
        console.print("\n[green]All configured models are accessible.[/green]")
        return

    console.print("[bold]Discovering available Bedrock models...[/bold]\n")
    all_models = get_available_models()

    table = Table(title="Available Models")
    table.add_column("Model ID", style="bold")
    table.add_column("Family")
    table.add_column("Gen")
    table.add_column("Status")
    for m in all_models:
        status = "[green]OK[/green]" if m.available else "[dim]--[/dim]"
        table.add_row(m.model_id, m.family, str(m.generation), status)
    console.print(table)

    latest = select_latest_per_family(all_models)
    console.print("\n[bold]Recommended defaults (latest per family):[/bold]")
    console.print(f"  Researcher: {latest.get('opus', 'N/A')}")
    console.print(f"  Worker:     {latest.get('sonnet', 'N/A')}")
    console.print(f"  Haiku:      {latest.get('haiku', 'N/A')}")


if __name__ == "__main__":
    app()
