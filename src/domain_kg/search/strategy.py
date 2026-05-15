"""Search strategy engine — determines HOW to search based on domain characteristics.

First principles:
- For academic/technical fields: find authoritative reviews first, then expand from citations
- For industry/market fields: find market reports and company pages first
- For clinical fields: find landmark trials and guidelines first

The strategy shapes what the research agents search for at each phase.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class DomainCharacter(str, Enum):
    academic = "academic"
    industry = "industry"
    clinical = "clinical"
    regulatory = "regulatory"
    mixed = "mixed"


class SearchPhase(BaseModel):
    """A phase of the search strategy with specific tactics."""

    name: str
    description: str
    tactics: list[str]
    source_priority: list[str]
    query_templates: list[str]


class SearchStrategy(BaseModel):
    """Complete search strategy for a domain characterization."""

    domain_character: DomainCharacter
    phases: list[SearchPhase]
    authoritative_sources: list[str]
    review_query_patterns: list[str]


# --- Strategy definitions ---

ACADEMIC_STRATEGY = SearchStrategy(
    domain_character=DomainCharacter.academic,
    phases=[
        SearchPhase(
            name="Find Authoritative Reviews",
            description="Start with highly-cited recent reviews from top journals to build foundational understanding",
            tactics=[
                "Search for systematic reviews and meta-analyses (most comprehensive)",
                "Look for Nature Reviews, Lancet, NEJM review articles",
                "Find papers with >100 citations in the last 3 years",
                "Identify review authors — they are likely KOLs",
            ],
            source_priority=["academic", "web"],
            query_templates=[
                "{domain} systematic review {year}",
                "{domain} review nature lancet",
                "{domain} state of the art overview",
                "{domain} comprehensive review recent advances",
            ],
        ),
        SearchPhase(
            name="Map Key Players from Reviews",
            description="Extract companies, technologies, and researchers cited in the reviews",
            tactics=[
                "Extract all company names mentioned in review papers",
                "Identify most-cited researchers (potential KOLs)",
                "Find technologies and methods described as 'promising' or 'emerging'",
                "Note which clinical trials are referenced as landmark studies",
            ],
            source_priority=["academic", "clinical_trials"],
            query_templates=[
                "{entity_name} clinical trial results",
                "{technology} validation study performance",
                "{company} {domain} product pipeline",
            ],
        ),
        SearchPhase(
            name="Deep Dive per Branch",
            description="Research each identified branch with targeted queries",
            tactics=[
                "For each branch, find the 2-3 most important papers",
                "Search for the specific technologies and their performance data",
                "Find clinical trials associated with key products",
                "Identify partnerships and acquisitions",
            ],
            source_priority=["academic", "web", "patents", "companies"],
            query_templates=[
                "{branch} key developments 2024 2025",
                "{branch} {domain} comparison performance",
                "{branch} clinical validation sensitivity specificity",
            ],
        ),
    ],
    authoritative_sources=[
        "Nature Reviews",
        "The Lancet",
        "NEJM",
        "Annual Review",
        "Cell",
        "Science",
    ],
    review_query_patterns=[
        '"{domain}" review OR "state of the art" OR "systematic review"',
        '"{domain}" "Nature Reviews" OR "Lancet" OR "Annual Review"',
    ],
)

INDUSTRY_STRATEGY = SearchStrategy(
    domain_character=DomainCharacter.industry,
    phases=[
        SearchPhase(
            name="Market Landscape Overview",
            description="Find market reports, analyst coverage, and industry maps",
            tactics=[
                "Search for market analysis reports and industry overviews",
                "Find company comparison articles and competitive landscapes",
                "Identify market leaders by revenue, funding, or market cap",
                "Look for recent M&A, partnerships, and funding rounds",
            ],
            source_priority=["web", "companies"],
            query_templates=[
                "{domain} market landscape companies 2025",
                "{domain} competitive analysis market leaders",
                "{domain} funding investment venture capital",
                "{domain} acquisitions partnerships strategic",
            ],
        ),
        SearchPhase(
            name="Company Deep Dives",
            description="Research each major company's products, pipeline, and strategy",
            tactics=[
                "Find SEC filings for public companies (10-K for strategy, 8-K for events)",
                "Search for product launches and pipeline updates",
                "Identify key executives and board members",
                "Find customer/partner announcements",
            ],
            source_priority=["companies", "web"],
            query_templates=[
                "{company} SEC 10-K annual report {domain}",
                "{company} product launch pipeline",
                "{company} CEO leadership team",
            ],
        ),
        SearchPhase(
            name="Technology and Differentiation",
            description="Understand the underlying technology differences between players",
            tactics=[
                "Search for patent filings to understand IP landscape",
                "Find technical comparisons and benchmarks",
                "Identify proprietary vs open-source approaches",
            ],
            source_priority=["patents", "academic", "web"],
            query_templates=[
                "{company} patent {technology} {domain}",
                "{domain} technology comparison benchmark",
            ],
        ),
    ],
    authoritative_sources=[
        "SEC EDGAR",
        "Crunchbase",
        "PitchBook",
        "BioPharma Dive",
        "FierceBiotech",
    ],
    review_query_patterns=[
        '"{domain}" market report landscape overview',
        '"{domain}" competitive analysis companies',
    ],
)

CLINICAL_STRATEGY = SearchStrategy(
    domain_character=DomainCharacter.clinical,
    phases=[
        SearchPhase(
            name="Landmark Trials and Guidelines",
            description="Find the definitive clinical trials and practice guidelines",
            tactics=[
                "Search ClinicalTrials.gov for Phase 3 and pivotal trials",
                "Find USPSTF, NCCN, and WHO guidelines related to the domain",
                "Identify FDA-approved products and their approval studies",
                "Look for real-world evidence and post-market studies",
            ],
            source_priority=["clinical_trials", "academic", "web"],
            query_templates=[
                "{domain} phase 3 pivotal trial results",
                "{domain} guideline recommendation USPSTF NCCN",
                "{domain} FDA approved 510k PMA",
                "{domain} real world evidence outcomes study",
            ],
        ),
        SearchPhase(
            name="Clinical Performance Data",
            description="Find sensitivity, specificity, and clinical utility data",
            tactics=[
                "Search for performance metrics (sensitivity, specificity, PPV, NPV)",
                "Find head-to-head comparisons between products/approaches",
                "Identify ongoing trials that will report in next 1-2 years",
                "Look for health economic and cost-effectiveness analyses",
            ],
            source_priority=["academic", "clinical_trials"],
            query_templates=[
                "{product} sensitivity specificity performance",
                "{domain} cost effectiveness health economics",
                "{domain} clinical utility outcomes evidence",
            ],
        ),
        SearchPhase(
            name="KOLs and Research Centers",
            description="Identify the key researchers and institutions driving the field",
            tactics=[
                "Find principal investigators of major trials",
                "Identify most-published authors in the field",
                "Locate major research centers and consortia",
                "Find advisory board members of key companies",
            ],
            source_priority=["academic", "web"],
            query_templates=[
                "{domain} principal investigator key researcher",
                "{domain} research center consortium",
                "{domain} conference keynote speaker expert",
            ],
        ),
    ],
    authoritative_sources=[
        "ClinicalTrials.gov",
        "FDA",
        "USPSTF",
        "NCCN",
        "WHO",
        "Cochrane",
    ],
    review_query_patterns=[
        '"{domain}" clinical trial landmark pivotal',
        '"{domain}" guideline recommendation screening',
    ],
)


def classify_domain(description: str, entity_types: list[str]) -> DomainCharacter:
    """Classify a domain's character based on description and entity types."""
    desc_lower = description.lower()

    academic_signals = ["research", "study", "mechanism", "biology", "molecular", "genomic"]
    clinical_signals = ["trial", "patient", "screening", "diagnosis", "treatment", "clinical"]
    industry_signals = ["company", "market", "product", "commercial", "business", "funding"]

    scores = {
        DomainCharacter.academic: sum(1 for s in academic_signals if s in desc_lower),
        DomainCharacter.clinical: sum(1 for s in clinical_signals if s in desc_lower),
        DomainCharacter.industry: sum(1 for s in industry_signals if s in desc_lower),
    }

    type_boost = {
        "company": DomainCharacter.industry,
        "organization": DomainCharacter.industry,
        "product": DomainCharacter.industry,
        "disease": DomainCharacter.clinical,
        "drug": DomainCharacter.clinical,
        "method": DomainCharacter.academic,
        "technology": DomainCharacter.academic,
    }
    for et in entity_types:
        if et in type_boost:
            scores[type_boost[et]] = scores.get(type_boost[et], 0) + 1

    max_score = max(scores.values())
    if max_score == 0 or list(scores.values()).count(max_score) > 1:
        return DomainCharacter.mixed

    return max(scores, key=scores.get)


def get_strategy(domain_character: DomainCharacter) -> SearchStrategy:
    """Get the appropriate search strategy for a domain character."""
    strategies = {
        DomainCharacter.academic: ACADEMIC_STRATEGY,
        DomainCharacter.industry: INDUSTRY_STRATEGY,
        DomainCharacter.clinical: CLINICAL_STRATEGY,
        DomainCharacter.mixed: CLINICAL_STRATEGY,  # default to clinical for biomedical
        DomainCharacter.regulatory: CLINICAL_STRATEGY,
    }
    return strategies[domain_character]


def build_strategy_for_domain(
    description: str,
    entity_types: list[str],
) -> SearchStrategy:
    """Classify domain and return the best search strategy."""
    character = classify_domain(description, entity_types)
    return get_strategy(character)
