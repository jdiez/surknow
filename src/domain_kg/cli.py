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
    format: str = typer.Option("json", "--format", "-f", help="Export format: json, csv, text"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output file or directory path"),
) -> None:
    """Export the knowledge graph in various formats."""
    import json as json_lib

    from domain_kg.db.client import get_client
    from domain_kg.db.queries import QueryHelper

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
    input_file: Path = typer.Argument(..., help="Domain input file (YAML/CSV/text)"),
    config_file: Path | None = typer.Option(None, "--config", "-c", help="Domain config file"),
    output_dir: Path = typer.Option(Path("output"), "--output", "-o", help="Output directory for text results"),
    max_iterations: int = typer.Option(3, "--max-iterations", "-n", help="Maximum iteration rounds"),
    coverage: float = typer.Option(0.8, "--coverage", help="Target coverage threshold"),
    resume: bool = typer.Option(True, "--resume/--fresh", help="Resume from last completed stage (default: resume)"),
) -> None:
    """Run pipeline and output results to text files in a directory.

    Saves intermediate JSON after each stage. On re-run (--resume), skips
    stages whose output already exists in the output directory.
    """
    import json as json_lib

    from domain_kg.flows.discover import discover_branches
    from domain_kg.flows.search import plan_searches
    from domain_kg.flows.understand import understand_domain
    from domain_kg.flows.vocabulary import gather_vocabulary
    from domain_kg.models import BranchTree, DomainContext, SearchPlan, VocabularyIndex
    from domain_kg.parsers import parse_input

    settings = Settings(max_iterations=max_iterations, coverage_threshold=coverage)
    output_dir.mkdir(parents=True, exist_ok=True)

    state_dir = output_dir / ".state"
    state_dir.mkdir(exist_ok=True)

    def _load_state(stage: str):
        path = state_dir / f"{stage}.json"
        if resume and path.exists():
            return json_lib.loads(path.read_text())
        return None

    def _save_state(stage: str, data):
        path = state_dir / f"{stage}.json"
        path.write_text(json_lib.dumps(data, indent=2, default=str))

    async def _run():
        domain_input = await parse_input(input_file)

        # Stage 1: Understand
        cached = _load_state("understand")
        if cached:
            context = DomainContext(**cached)
            console.print("[dim]Stage 1 (understand): resumed from cache[/dim]")
        else:
            context = await understand_domain(domain_input)
            _save_state("understand", context.model_dump())
            console.print("[green]Stage 1 (understand): completed[/green]")

        # Stage 2: Discover branches
        cached = _load_state("branches")
        if cached:
            branches = BranchTree(**cached)
            console.print("[dim]Stage 2 (branches): resumed from cache[/dim]")
        else:
            branches = await discover_branches(context, 0)
            _save_state("branches", branches.model_dump())
            console.print("[green]Stage 2 (branches): completed[/green]")

        # Stage 3: Vocabulary
        cached = _load_state("vocabulary")
        if cached:
            vocab = VocabularyIndex(**cached)
            console.print("[dim]Stage 3 (vocabulary): resumed from cache[/dim]")
        else:
            vocab = await gather_vocabulary(branches, settings)
            _save_state("vocabulary", vocab.model_dump())
            console.print("[green]Stage 3 (vocabulary): completed[/green]")

        # Stage 4: Search plan
        cached = _load_state("search_plan")
        if cached:
            search_plan = SearchPlan(**cached)
            console.print("[dim]Stage 4 (search plan): resumed from cache[/dim]")
        else:
            search_plan = await plan_searches(branches, vocab, settings)
            _save_state("search_plan", search_plan.model_dump())
            console.print("[green]Stage 4 (search plan): completed[/green]")

        return context, branches, vocab, search_plan

    console.print(f"[bold green]Running characterization:[/bold green] {input_file}")
    if resume:
        console.print(f"[dim]Resume mode: checking {state_dir} for cached stages[/dim]")
    context, branches, vocab, search_plan = asyncio.run(_run())

    domain_slug = context.domain.lower().replace(" ", "_")

    # Write human-readable text output
    (output_dir / f"{domain_slug}_understanding.txt").write_text(
        f"Domain: {context.domain}\n"
        f"Description: {context.description}\n\n"
        f"Entity Types:\n" + "\n".join(f"  - {t}" for t in context.initial_entity_types) + "\n\n"
        f"Relation Types:\n" + "\n".join(f"  - {r}" for r in context.initial_relation_types) + "\n\n"
        f"Boundaries:\n" + "\n".join(f"  {b}" for b in context.boundaries) + "\n\n"
        f"Adjacent Fields:\n" + "\n".join(f"  - {f}" for f in context.adjacent_fields) + "\n"
    )

    branch_lines = []
    for b in branches.branches:
        indent = "  " * b.depth
        branch_lines.append(f"  {indent}{b.name} (conf={b.confidence:.2f}) — {b.description}")
    (output_dir / f"{domain_slug}_branches.txt").write_text(
        f"Domain: {context.domain}\n"
        f"Total Branches: {len(branches.branches)}\n"
        f"Coverage: {branches.coverage_pct:.0f}%\n\n"
        + "\n".join(branch_lines) + "\n"
    )

    vocab_lines = []
    for t in vocab.terms:
        aliases = f" (aka: {', '.join(t.aliases)})" if t.aliases else ""
        vocab_lines.append(f"  [{t.branch}] {t.canonical}{aliases}")
    (output_dir / f"{domain_slug}_vocabulary.txt").write_text(
        f"Domain: {context.domain}\n"
        f"Total Terms: {len(vocab.terms)}\n\n"
        + "\n".join(vocab_lines) + "\n"
    )

    query_lines = []
    for q in search_plan.queries:
        query_lines.append(f"  [{q.source_type}] {q.query}")
        query_lines.append(f"    expects: {q.expected_entity_types}")
    (output_dir / f"{domain_slug}_search_plan.txt").write_text(
        f"Domain: {context.domain}\n"
        f"Total Queries: {len(search_plan.queries)}\n\n"
        + "\n".join(query_lines) + "\n"
    )

    console.print(f"[green]Output written to {output_dir}/[/green]")
    console.print(f"  {domain_slug}_understanding.txt")
    console.print(f"  {domain_slug}_branches.txt")
    console.print(f"  {domain_slug}_vocabulary.txt")
    console.print(f"  {domain_slug}_search_plan.txt")


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


if __name__ == "__main__":
    app()
