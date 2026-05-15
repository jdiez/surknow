"""Learning store — persists successful patterns from past runs.

After each successful pipeline run, we save:
- Which branches were discovered for a domain type
- Which search queries produced the most/best entities
- Which entity types were most common per branch
- Which sources (URLs, journals) were most authoritative

Future runs for similar domains can bootstrap from these learnings.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

LEARNING_DIR = Path("learning")


class QueryLearning(BaseModel):
    """What we learned from a specific search query."""

    query: str
    source_type: str
    branch: str
    entities_found: int
    high_confidence_entities: int
    useful: bool


class BranchLearning(BaseModel):
    """What we learned about researching a specific branch."""

    branch_name: str
    domain_character: str
    effective_queries: list[str]
    ineffective_queries: list[str]
    entity_types_found: dict[str, int]
    best_sources: list[str]


class RunLearning(BaseModel):
    """Complete learning from a single pipeline run."""

    domain: str
    domain_character: str
    run_id: str
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    branches_discovered: list[str]
    total_entities: int
    total_relationships: int
    coverage_achieved: float
    branch_learnings: list[BranchLearning] = []
    query_learnings: list[QueryLearning] = []
    effective_branch_queries: dict[str, list[str]] = {}
    notes: list[str] = []


def save_run_learning(learning: RunLearning, learning_dir: Path | None = None) -> Path:
    """Save learning from a completed run."""
    base = learning_dir or LEARNING_DIR
    base.mkdir(parents=True, exist_ok=True)

    domain_slug = learning.domain.lower().replace(" ", "_").replace("-", "_")
    filename = f"{domain_slug}_{learning.run_id}.yaml"
    path = base / filename

    path.write_text(
        yaml.dump(
            learning.model_dump(mode="json"),
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )
    )

    # Also update the domain index
    _update_domain_index(learning, base)

    return path


def load_domain_learnings(domain: str, learning_dir: Path | None = None) -> list[RunLearning]:
    """Load all past learnings for a domain."""
    base = learning_dir or LEARNING_DIR
    if not base.exists():
        return []

    domain_slug = domain.lower().replace(" ", "_").replace("-", "_")
    learnings = []

    for path in sorted(base.glob(f"{domain_slug}_*.yaml")):
        if path.name == "index.yaml":
            continue
        try:
            data = yaml.safe_load(path.read_text())
            learnings.append(RunLearning(**data))
        except Exception:
            continue

    return learnings


def get_effective_queries(domain: str, branch: str, learning_dir: Path | None = None) -> list[str]:
    """Get queries that worked well for a domain+branch in past runs."""
    learnings = load_domain_learnings(domain, learning_dir)
    queries = []

    for learning in learnings:
        branch_queries = learning.effective_branch_queries.get(branch, [])
        queries.extend(branch_queries)

        for ql in learning.query_learnings:
            if ql.branch == branch and ql.useful and ql.entities_found > 2:
                queries.append(ql.query)

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for q in queries:
        if q not in seen:
            seen.add(q)
            unique.append(q)

    return unique


def get_known_branches(domain: str, learning_dir: Path | None = None) -> list[str]:
    """Get branches discovered in past runs for this domain."""
    learnings = load_domain_learnings(domain, learning_dir)
    branches = set()
    for learning in learnings:
        branches.update(learning.branches_discovered)
    return sorted(branches)


def get_best_sources(domain: str, learning_dir: Path | None = None) -> list[str]:
    """Get sources that consistently produce high-quality entities."""
    learnings = load_domain_learnings(domain, learning_dir)
    sources: dict[str, int] = {}

    for learning in learnings:
        for bl in learning.branch_learnings:
            for src in bl.best_sources:
                sources[src] = sources.get(src, 0) + 1

    return sorted(sources, key=sources.get, reverse=True)[:20]


def build_learning_context(domain: str, learning_dir: Path | None = None) -> str:
    """Build a context string from past learnings to inject into agent prompts."""
    learnings = load_domain_learnings(domain, learning_dir)
    if not learnings:
        return ""

    latest = learnings[-1]
    lines = [
        f"PRIOR KNOWLEDGE (from {len(learnings)} previous runs):",
        f"  Known branches: {', '.join(latest.branches_discovered)}",
        f"  Best coverage achieved: {max(l.coverage_achieved for l in learnings):.0%}",
    ]

    effective = get_effective_queries(domain, branch="", learning_dir=learning_dir)
    if effective:
        lines.append(f"  Effective query patterns: {effective[:5]}")

    sources = get_best_sources(domain, learning_dir)
    if sources:
        lines.append(f"  Authoritative sources: {sources[:5]}")

    if latest.notes:
        lines.append(f"  Notes: {'; '.join(latest.notes[:3])}")

    return "\n".join(lines)


def _update_domain_index(learning: RunLearning, base: Path) -> None:
    """Update the domain index file with latest run info."""
    index_path = base / "index.yaml"
    index: dict = {}

    if index_path.exists():
        index = yaml.safe_load(index_path.read_text()) or {}

    domain_slug = learning.domain.lower().replace(" ", "_")
    if domain_slug not in index:
        index[domain_slug] = {
            "domain": learning.domain,
            "runs": [],
            "best_coverage": 0.0,
        }

    entry = index[domain_slug]
    entry["runs"].append({
        "run_id": learning.run_id,
        "timestamp": learning.timestamp,
        "entities": learning.total_entities,
        "coverage": learning.coverage_achieved,
    })
    entry["best_coverage"] = max(entry["best_coverage"], learning.coverage_achieved)

    index_path.write_text(
        yaml.dump(index, default_flow_style=False, sort_keys=False)
    )
