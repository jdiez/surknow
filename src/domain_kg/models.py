"""Domain knowledge graph pipeline models."""

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field


class EntityType(str, Enum):
    person = "person"
    organization = "organization"
    method = "method"
    tool = "tool"
    paper = "paper"
    concept = "concept"
    disease = "disease"
    drug = "drug"
    target = "target"
    technology = "technology"
    product = "product"
    standard = "standard"
    custom = "custom"


class Provenance(BaseModel):
    source: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    agent: str
    model: str
    search_query: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    iteration: int = 0


class SeedEntity(BaseModel):
    name: str
    type: str
    description: str | None = None


class SeedLink(BaseModel):
    source: str
    target: str
    relation: str


class DomainInput(BaseModel):
    domain: str
    description: str
    entities: list[SeedEntity] = []
    links: list[SeedLink] = []


class DomainContext(BaseModel):
    domain: str
    description: str
    boundaries: list[str]
    adjacent_fields: list[str]
    initial_entity_types: list[str]
    initial_relation_types: list[str]
    seed_entities: list[SeedEntity]
    seed_links: list[SeedLink]


class Branch(BaseModel):
    name: str
    parent: str | None = None
    depth: int = 0
    description: str
    confidence: float
    coverage: float = 0.0


class BranchTree(BaseModel):
    branches: list[Branch]
    coverage_pct: float
    iteration: int


class Term(BaseModel):
    canonical: str
    definition: str | None = None
    aliases: list[str] = []
    branch: str
    provenance: Provenance


class VocabularyIndex(BaseModel):
    terms: list[Term]
    branch_coverage: dict[str, int]


class SearchQuery(BaseModel):
    query: str
    branch: str
    source_type: str
    expected_entity_types: list[str]
    priority: int


class SearchPlan(BaseModel):
    queries: list[SearchQuery]
    total_branches: int
    covered_branches: int


class Entity(BaseModel):
    name: str
    entity_type: EntityType
    description: str | None = None
    branch: str | None = None
    aliases: list[str] = []
    provenance: Provenance
    metadata: dict = {}


class Relationship(BaseModel):
    source: str
    target: str
    relation_type: str
    confidence: float
    provenance: Provenance


class CoverageMetrics(BaseModel):
    branches_covered: int
    total_branches: int
    coverage_pct: float
    entities_total: int
    relationships_total: int

    def meets_threshold(self, threshold: float) -> bool:
        return self.coverage_pct >= threshold


class KGResult(BaseModel):
    entities_created: int
    relationships_created: int
    entities_merged: int
    branches_covered: int
    total_branches: int
    coverage_pct: float
    iterations_used: int
    schema_discovered: list[str]


class ToolDefinition(BaseModel):
    name: str
    type: str
    uri: str | None = None
    api_key_env: str | None = None
    domains: list[str] = []
    priority: int = 0
    rate_limit: int | None = None


class ToolRegistry(BaseModel):
    generic: list[ToolDefinition]
    field_specific: dict[str, list[ToolDefinition]]
    mcp_servers: list[ToolDefinition] = []
