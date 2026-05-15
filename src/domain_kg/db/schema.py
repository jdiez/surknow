"""SurrealDB schema definitions."""

SCHEMA_DDL = """
-- Entity table
DEFINE TABLE entity SCHEMAFULL;
DEFINE FIELD name ON entity TYPE string;
DEFINE FIELD entity_type ON entity TYPE string;
DEFINE FIELD description ON entity TYPE option<string>;
DEFINE FIELD branch ON entity TYPE option<string>;
DEFINE FIELD confidence ON entity TYPE float;
DEFINE FIELD provenance ON entity TYPE object;
DEFINE FIELD provenance.source ON entity TYPE string;
DEFINE FIELD provenance.timestamp ON entity TYPE datetime;
DEFINE FIELD provenance.agent ON entity TYPE string;
DEFINE FIELD provenance.model ON entity TYPE string;
DEFINE FIELD provenance.search_query ON entity TYPE option<string>;
DEFINE FIELD aliases ON entity TYPE option<array<string>>;
DEFINE FIELD metadata ON entity TYPE option<object>;

-- Edge types
DEFINE TABLE relates_to SCHEMAFULL;
DEFINE FIELD relation_type ON relates_to TYPE string;
DEFINE FIELD confidence ON relates_to TYPE float;
DEFINE FIELD provenance ON relates_to TYPE object;
DEFINE FIELD provenance.source ON relates_to TYPE string;
DEFINE FIELD provenance.timestamp ON relates_to TYPE datetime;
DEFINE FIELD provenance.agent ON relates_to TYPE string;
DEFINE FIELD direction ON relates_to TYPE option<string>;

-- Domain metadata
DEFINE TABLE domain SCHEMAFULL;
DEFINE FIELD name ON domain TYPE string;
DEFINE FIELD description ON domain TYPE string;
DEFINE FIELD boundaries ON domain TYPE array<string>;
DEFINE FIELD created ON domain TYPE datetime;
DEFINE FIELD input_file ON domain TYPE string;

-- Branch hierarchy
DEFINE TABLE branch SCHEMAFULL;
DEFINE FIELD name ON branch TYPE string;
DEFINE FIELD parent ON branch TYPE option<record<branch>>;
DEFINE FIELD depth ON branch TYPE int;
DEFINE FIELD coverage ON branch TYPE float;
DEFINE FIELD entity_count ON branch TYPE int;

-- Vocabulary
DEFINE TABLE term SCHEMAFULL;
DEFINE FIELD canonical ON term TYPE string;
DEFINE FIELD definition ON term TYPE option<string>;
DEFINE FIELD aliases ON term TYPE array<string>;
DEFINE FIELD branch ON term TYPE record<branch>;

-- Provenance source documents
DEFINE TABLE source SCHEMAFULL;
DEFINE FIELD url ON source TYPE string;
DEFINE FIELD title ON source TYPE option<string>;
DEFINE FIELD retrieved_at ON source TYPE datetime;
DEFINE FIELD content_hash ON source TYPE option<string>;

-- Processing log
DEFINE TABLE processing_log SCHEMAFULL;
DEFINE FIELD run_id ON processing_log TYPE string;
DEFINE FIELD stage ON processing_log TYPE string;
DEFINE FIELD input_hash ON processing_log TYPE string;
DEFINE FIELD status ON processing_log TYPE string;
DEFINE FIELD started_at ON processing_log TYPE datetime;
DEFINE FIELD completed_at ON processing_log TYPE option<datetime>;
DEFINE FIELD entities_added ON processing_log TYPE int DEFAULT 0;
DEFINE FIELD relations_added ON processing_log TYPE int DEFAULT 0;
DEFINE FIELD iteration ON processing_log TYPE int;
DEFINE FIELD search_queries_executed ON processing_log TYPE array DEFAULT [];
DEFINE FIELD sources_processed ON processing_log TYPE array DEFAULT [];

-- Indexes
DEFINE INDEX entity_name ON entity FIELDS name;
DEFINE INDEX entity_type_idx ON entity FIELDS entity_type;
DEFINE INDEX term_canonical ON term FIELDS canonical;
DEFINE INDEX source_url ON source FIELDS url UNIQUE;
DEFINE INDEX log_run ON processing_log FIELDS run_id;
DEFINE INDEX log_hash ON processing_log FIELDS input_hash, stage;
"""


async def apply_schema(client, force: bool = False) -> None:
    """Apply the full schema DDL to SurrealDB."""
    import structlog
    logger = structlog.get_logger("domain_kg.db.schema")

    if not force:
        try:
            await client.query("INFO FOR TABLE entity;")
            logger.info("schema.already_exists")
            return
        except Exception:
            pass

    statements = [s.strip() for s in SCHEMA_DDL.strip().split(";") if s.strip() and not s.strip().startswith("--")]
    for stmt in statements:
        await client.query(stmt + ";")
    logger.info("schema.applied", statements=len(statements))
