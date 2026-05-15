"""Research flow — iterative branch-by-branch domain understanding.

First principles approach:
1. Classify domain → select search strategy (academic, clinical, industry)
2. Discover branches (small Opus call → field structure, informed by past learnings)
3. Research each branch independently (parallel Sonnet calls → entities per branch)
4. Synthesize into final ResearchBrief (data merging, no LLM)
5. Save learnings for future runs

Strategy drives HOW to search:
- Academic: start with authoritative reviews, then expand from citations
- Clinical: start with landmark trials and guidelines
- Industry: start with market reports and company analysis
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import structlog
import yaml
from agno.agent import Agent
from prefect import task

from domain_kg.agents.search_tools import (
    AcademicSearchToolkit,
    ClinicalTrialsToolkit,
    CompanySearchToolkit,
    WebSearchToolkit,
)
from domain_kg.agents.teams import _build_model
from domain_kg.config import Settings
from domain_kg.domain_config import DomainConfig
from domain_kg.learning.store import (
    BranchLearning,
    QueryLearning,
    RunLearning,
    build_learning_context,
    get_effective_queries,
    get_known_branches,
    save_run_learning,
)
from domain_kg.models import (
    ExpansionQuery,
    FieldBranch,
    ResearchBrief,
    RootEntity,
    SearchPlan,
    SearchQuery,
)
from domain_kg.search.strategy import SearchStrategy, build_strategy_for_domain

logger = structlog.get_logger("domain_kg.flows.research")


# --- Step 1: Discover field structure ---

BRANCH_DISCOVERY_PROMPT = """You are a domain expert. Given this field description, identify the 4-7 major branches (sub-areas) that structure this domain.

DOMAIN: {domain}
DESCRIPTION: {description}

{seed_context}

{learning_context}

SEARCH STRATEGY: This domain is characterized as "{domain_character}".
{strategy_guidance}

For each branch, provide:
- name: Short name (2-4 words)
- description: What this branch covers (1 sentence)
- search_queries: 2-3 specific search queries to find key entities in this branch. Use the strategy guidance above to craft effective queries.

Respond as JSON array:
[{{"name": "...", "description": "...", "search_queries": ["...", "..."]}}]
"""


async def _discover_branches(
    domain_config: DomainConfig,
    settings: Settings,
    strategy: SearchStrategy,
) -> list[dict]:
    """Step 1: Use Opus to identify the field's major branches, informed by strategy + learnings."""
    logger.info("research.step1.discover_branches", character=strategy.domain_character.value)

    model = _build_model(settings, settings.researcher_model_id)
    agent = Agent(
        name="BranchDiscovery",
        model=model,
        instructions=["Respond ONLY with the JSON array. No markdown, no explanation."],
        markdown=False,
    )

    seed_context = ""
    examples = domain_config.examples.get("entities", [])
    if examples:
        seed_context = "Known entities:\n" + "\n".join(
            f"  - {e.get('name', '')} ({e.get('type', '')})" for e in examples[:10]
        )

    # Build strategy guidance from first phase
    phase1 = strategy.phases[0] if strategy.phases else None
    strategy_guidance = ""
    if phase1:
        strategy_guidance = (
            f"RECOMMENDED APPROACH for Phase 1 ({phase1.name}):\n"
            f"  {phase1.description}\n"
            f"  Tactics: {'; '.join(phase1.tactics[:3])}\n"
            f"  Priority sources: {', '.join(phase1.source_priority)}\n"
            f"  Example queries: {phase1.query_templates[:2]}"
        )

    # Load learnings from past runs
    learning_context = build_learning_context(domain_config.domain)
    known_branches = get_known_branches(domain_config.domain)
    if known_branches:
        learning_context += f"\n  Previously discovered branches: {', '.join(known_branches)}"

    prompt = BRANCH_DISCOVERY_PROMPT.format(
        domain=domain_config.domain,
        description=domain_config.description,
        seed_context=seed_context,
        learning_context=learning_context,
        domain_character=strategy.domain_character.value,
        strategy_guidance=strategy_guidance,
    )

    response = await agent.arun(prompt)
    text = str(response.content)

    try:
        start = text.index("[")
        end = text.rindex("]") + 1
        branches = json.loads(text[start:end])
    except (ValueError, json.JSONDecodeError):
        logger.warning("research.step1.parse_failed", response=text[:200])
        branches = [
            {"name": "Core Technologies", "description": "Key technologies in the field", "search_queries": [f"{domain_config.domain} technologies"]},
            {"name": "Key Players", "description": "Companies and organizations", "search_queries": [f"{domain_config.domain} companies"]},
            {"name": "Clinical Applications", "description": "Clinical use and trials", "search_queries": [f"{domain_config.domain} clinical trials"]},
            {"name": "Research", "description": "Academic research and KOLs", "search_queries": [f"{domain_config.domain} research review"]},
        ]

    logger.info("research.step1.complete", branches=len(branches))
    return branches


# --- Step 2: Research each branch ---

BRANCH_RESEARCH_PROMPT = """Research this specific branch of "{domain}":

BRANCH: {branch_name}
DESCRIPTION: {branch_description}

SEARCH STRATEGY: {strategy_phase}

{prior_queries}

Use your search tools to find the KEY ENTITIES in this branch. Focus on:
- The most important companies, organizations, or people
- Key technologies, products, or methods
- Important papers, trials, or standards
- For academic topics: start with recent review papers from top journals, then extract key entities mentioned

For each entity found, provide:
- name: Canonical name
- entity_type: One of {entity_types}
- description: What it is (1-2 sentences)
- why_important: Why it matters to this field
- source_url: Where you found it

Also suggest 3-5 expansion queries for deeper investigation of this branch.

Respond as JSON:
{{"entities": [...], "expansion_queries": [...]}}
"""


async def _research_branch(
    branch: dict,
    domain_config: DomainConfig,
    settings: Settings,
    strategy: SearchStrategy,
) -> dict:
    """Step 2: Research a single branch using search tools, guided by strategy."""
    logger.info("research.step2.branch_started", branch=branch["name"])

    model = _build_model(settings, settings.worker_model_id)
    agent = Agent(
        name=f"BranchResearcher_{branch['name'].replace(' ', '_')}",
        model=model,
        tools=[
            WebSearchToolkit(settings),
            AcademicSearchToolkit(settings),
            ClinicalTrialsToolkit(),
            CompanySearchToolkit(),
        ],
        instructions=[
            "You are a domain researcher. Use search tools to find entities.",
            "Start with the most authoritative sources (reviews, landmark papers, official reports).",
            "Then extract key entities from what you find.",
            "Respond ONLY with the JSON object. No markdown fences.",
        ],
        tool_call_limit=15,
        markdown=False,
    )

    entity_types = domain_config.get_entity_types() or [
        "company", "person", "technology", "product", "concept", "disease", "drug"
    ]

    # Build strategy phase guidance
    phase_idx = min(1, len(strategy.phases) - 1)
    phase = strategy.phases[phase_idx]
    strategy_phase = (
        f"{phase.name}: {phase.description}\n"
        f"  Tactics: {'; '.join(phase.tactics[:2])}\n"
        f"  Priority sources: {', '.join(phase.source_priority)}"
    )

    # Include effective queries from past runs
    prior = get_effective_queries(domain_config.domain, branch["name"])
    prior_queries = ""
    if prior:
        prior_queries = f"PREVIOUSLY EFFECTIVE QUERIES for this branch:\n  " + "\n  ".join(prior[:5])

    prompt = BRANCH_RESEARCH_PROMPT.format(
        domain=domain_config.domain,
        branch_name=branch["name"],
        branch_description=branch["description"],
        entity_types=", ".join(entity_types),
        strategy_phase=strategy_phase,
        prior_queries=prior_queries,
    )

    response = await agent.arun(prompt)
    text = str(response.content)

    try:
        start = text.index("{")
        end = text.rindex("}") + 1
        result = json.loads(text[start:end])
    except (ValueError, json.JSONDecodeError):
        logger.warning("research.step2.parse_failed", branch=branch["name"], response=text[:200])
        result = {"entities": [], "expansion_queries": []}

    entity_count = len(result.get("entities", []))
    logger.info("research.step2.branch_complete", branch=branch["name"], entities=entity_count)
    return {**result, "branch_name": branch["name"], "branch_description": branch["description"]}


# --- Step 3: Synthesize ---

def _synthesize_brief(
    domain_config: DomainConfig,
    branches: list[dict],
    branch_results: list[dict],
) -> ResearchBrief:
    """Step 3: Merge branch research into a ResearchBrief (no LLM call needed)."""
    root_entities = []
    expansion_plan = []
    field_map = []
    sources: set[str] = set()

    for result in branch_results:
        branch_name = result.get("branch_name", "unknown")

        field_map.append(FieldBranch(
            name=branch_name,
            description=result.get("branch_description", ""),
            key_entities=[e.get("name", "") for e in result.get("entities", [])[:5]],
            depth_priority=1,
        ))

        for entity in result.get("entities", []):
            source_url = entity.get("source_url", "")
            if source_url:
                sources.add(source_url)

            root_entities.append(RootEntity(
                name=entity.get("name", "Unknown"),
                entity_type=entity.get("entity_type", "concept"),
                description=entity.get("description", ""),
                why_root=entity.get("why_important", ""),
                confidence=0.8,
                source_urls=[source_url] if source_url else [],
                aliases=entity.get("aliases", []),
            ))

        for eq in result.get("expansion_queries", []):
            if isinstance(eq, str):
                expansion_plan.append(ExpansionQuery(
                    query=eq,
                    source_type="web",
                    branch=branch_name,
                    expected_entity_types=[],
                    rationale=f"Deeper investigation of {branch_name}",
                ))
            elif isinstance(eq, dict):
                expansion_plan.append(ExpansionQuery(
                    query=eq.get("query", ""),
                    source_type=eq.get("source_type", "web"),
                    branch=branch_name,
                    expected_entity_types=eq.get("expected_entity_types", []),
                    rationale=eq.get("rationale", f"Expansion of {branch_name}"),
                ))

    understanding = (
        f"{domain_config.domain} is structured across {len(field_map)} major branches: "
        + ", ".join(b.name for b in field_map) + ". "
        f"Initial research identified {len(root_entities)} root entities across these branches."
    )

    return ResearchBrief(
        domain=domain_config.domain,
        understanding=understanding,
        root_entities=root_entities,
        field_map=field_map,
        expansion_plan=expansion_plan,
        sources_consulted=list(sources),
        confidence=min(0.9, 0.5 + 0.1 * len(branch_results)),
        iterations_used=1,
    )


# --- Main entry point ---

@task(name="run-research-team")
async def run_research_team(
    domain_config: DomainConfig,
    settings: Settings,
    output_dir: Path,
    run_id: str,
) -> ResearchBrief:
    """Iterative research: classify → discover branches → research each → synthesize → learn."""
    logger.info("research_team.started", domain=domain_config.domain)

    # Step 0: Classify domain and select search strategy
    entity_types = domain_config.get_entity_types()
    strategy = build_strategy_for_domain(domain_config.description, entity_types)
    logger.info("research.strategy_selected", character=strategy.domain_character.value)

    # Step 1: Discover branches (single fast Opus call, informed by strategy + learnings)
    branches = await _discover_branches(domain_config, settings, strategy)

    # Step 2: Research each branch (parallel Sonnet calls with tools)
    branch_tasks = [
        _research_branch(branch, domain_config, settings, strategy)
        for branch in branches
    ]
    branch_results = await asyncio.gather(*branch_tasks, return_exceptions=True)

    # Filter out failed branches
    valid_results = []
    for i, result in enumerate(branch_results):
        if isinstance(result, Exception):
            logger.error("research.branch_failed", branch=branches[i]["name"], error=str(result))
        else:
            valid_results.append(result)

    # Step 3: Synthesize (no LLM call — just data merging)
    brief = _synthesize_brief(domain_config, branches, valid_results)

    _save_research_brief(brief, output_dir / run_id)

    # Step 4: Save learnings for future runs
    _save_learnings(domain_config, strategy, brief, valid_results, run_id, output_dir)

    logger.info(
        "research_team.complete",
        root_entities=len(brief.root_entities),
        branches=len(brief.field_map),
        expansion_queries=len(brief.expansion_plan),
        confidence=brief.confidence,
    )

    return brief


def _save_learnings(
    domain_config: DomainConfig,
    strategy: SearchStrategy,
    brief: ResearchBrief,
    branch_results: list[dict],
    run_id: str,
    output_dir: Path,
) -> None:
    """Save what we learned from this run for future improvements."""
    branch_learnings = []
    effective_branch_queries: dict[str, list[str]] = {}

    for result in branch_results:
        branch_name = result.get("branch_name", "unknown")
        entities = result.get("entities", [])
        expansion = result.get("expansion_queries", [])

        entity_type_counts: dict[str, int] = {}
        for e in entities:
            et = e.get("entity_type", "unknown")
            entity_type_counts[et] = entity_type_counts.get(et, 0) + 1

        sources = [e.get("source_url", "") for e in entities if e.get("source_url")]

        # Queries that produced entities are effective
        effective_qs = [
            eq if isinstance(eq, str) else eq.get("query", "")
            for eq in expansion
            if eq
        ]
        if effective_qs:
            effective_branch_queries[branch_name] = effective_qs

        branch_learnings.append(BranchLearning(
            branch_name=branch_name,
            domain_character=strategy.domain_character.value,
            effective_queries=effective_qs[:5],
            ineffective_queries=[],
            entity_types_found=entity_type_counts,
            best_sources=sources[:5],
        ))

    learning = RunLearning(
        domain=domain_config.domain,
        domain_character=strategy.domain_character.value,
        run_id=run_id,
        branches_discovered=[b.name for b in brief.field_map],
        total_entities=len(brief.root_entities),
        total_relationships=0,
        coverage_achieved=brief.confidence,
        branch_learnings=branch_learnings,
        effective_branch_queries=effective_branch_queries,
    )

    learning_dir = output_dir / "learning"
    save_run_learning(learning, learning_dir)
    logger.info("research.learnings_saved", domain=domain_config.domain)


# --- Utilities ---

def brief_to_search_plan(brief: ResearchBrief) -> SearchPlan:
    """Convert a ResearchBrief's expansion_plan into a SearchPlan for execution."""
    queries = []
    for i, eq in enumerate(brief.expansion_plan):
        queries.append(
            SearchQuery(
                query=eq.query,
                branch=eq.branch,
                source_type=eq.source_type,
                expected_entity_types=eq.expected_entity_types,
                priority=i // 10 + 1,
            )
        )

    branches = {eq.branch for eq in brief.expansion_plan}
    return SearchPlan(
        queries=queries,
        total_branches=len(branches),
        covered_branches=0,
    )


def _save_research_brief(brief: ResearchBrief, output_dir: Path) -> None:
    """Save the research brief as YAML and JSON."""
    output_dir.mkdir(parents=True, exist_ok=True)

    yaml_path = output_dir / "research_brief.yaml"
    yaml_path.write_text(
        yaml.dump(
            brief.model_dump(mode="json"),
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )
    )

    json_path = output_dir / "research_brief.json"
    json_path.write_text(json.dumps(brief.model_dump(mode="json"), indent=2))

    logger.info("research_brief.saved", path=str(output_dir))
