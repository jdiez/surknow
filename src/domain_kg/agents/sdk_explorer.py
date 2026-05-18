"""Claude Code SDK agents for grounded domain exploration."""

from __future__ import annotations

import asyncio
import json
import re

import structlog

from domain_kg.models import (
    BranchTree,
    DomainContext,
    DomainInput,
    VocabularyIndex,
)

logger = structlog.get_logger("domain_kg.agents.sdk_explorer")


def _extract_json(text: str) -> str:
    """Extract JSON object/array from agent text output."""
    text = text.strip()
    try:
        json.loads(text)
        return text
    except json.JSONDecodeError:
        pass

    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        candidate = match.group(1).strip()
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            pass

    for start_char, end_char in [("{", "}"), ("[", "]")]:
        start = text.find(start_char)
        if start == -1:
            continue
        end = text.rfind(end_char)
        if end > start:
            candidate = text[start : end + 1]
            try:
                json.loads(candidate)
                return candidate
            except json.JSONDecodeError:
                continue

    raise ValueError(f"No valid JSON found in text: {text[:200]}...")


async def _run_sdk_query(prompt: str, system: str, max_turns: int = 15) -> str:
    """Run a Claude Code SDK query and return the final text output."""
    from claude_code_sdk import ClaudeCodeOptions, query

    options = ClaudeCodeOptions(
        permission_mode="bypassPermissions",
        model="sonnet",
        max_turns=max_turns,
        allowed_tools=["WebSearch", "Read"],
        disallowed_tools=["Edit", "Write", "Agent", "Bash"],
        append_system_prompt=system,
    )

    result_text = ""
    async for message in query(prompt=prompt, options=options):
        if hasattr(message, "content"):
            for block in message.content:
                if hasattr(block, "text") and block.text:
                    result_text = block.text

    return result_text


async def understand_domain_sdk(domain_input: DomainInput) -> DomainContext:
    """Stage 1: Use Claude Code SDK to understand domain with real web search."""
    logger.info("sdk.stage1.started", domain=domain_input.domain)

    seed_entities_text = ""
    if domain_input.entities:
        seed_entities_text = "Known seed entities:\n" + "\n".join(
            f"  - {e.name} ({e.type}): {e.description or ''}"
            for e in domain_input.entities[:10]
        )

    seed_links_text = ""
    if domain_input.links:
        seed_links_text = "Known relationships:\n" + "\n".join(
            f"  - {l.source} --[{l.relation}]--> {l.target}"
            for l in domain_input.links[:10]
        )

    prompt = f"""Research this domain and produce a structured understanding.

DOMAIN: {domain_input.domain}
DESCRIPTION: {domain_input.description}

{seed_entities_text}
{seed_links_text}

TASK:
1. Search the web to verify this domain exists and understand its current scope
2. Identify what entity types are relevant (companies, products, technologies, diseases, people, etc.)
3. Identify relationship types between entities (develops, uses, targets, etc.)
4. Establish clear IN-SCOPE and OUT-OF-SCOPE boundaries
5. Identify adjacent/overlapping fields

You MUST output ONLY a JSON object with this exact structure (no other text):
{{
  "domain": "{domain_input.domain}",
  "description": "expanded description based on research...",
  "boundaries": ["IN: ...", "IN: ...", "OUT: ...", "OUT: ..."],
  "adjacent_fields": ["field1", "field2", ...],
  "initial_entity_types": ["type1", "type2", ...],
  "initial_relation_types": ["rel1", "rel2", ...],
  "seed_entities": [],
  "seed_links": []
}}"""

    system = (
        "You are a domain research agent. Use web search to verify claims. "
        "Output ONLY valid JSON — no markdown fences, no explanation, no preamble."
    )

    try:
        async with asyncio.timeout(120):
            result_text = await _run_sdk_query(prompt, system, max_turns=15)
            raw_json = _extract_json(result_text)
            data = json.loads(raw_json)

            data["seed_entities"] = [e.model_dump() for e in domain_input.entities]
            data["seed_links"] = [l.model_dump() for l in domain_input.links]

            context = DomainContext(**data)
            logger.info("sdk.stage1.completed", domain=context.domain)
            return context

    except (asyncio.TimeoutError, ValueError, json.JSONDecodeError, Exception) as e:
        logger.warning("sdk.stage1.failed", error=str(e), fallback="agno")
        raise
