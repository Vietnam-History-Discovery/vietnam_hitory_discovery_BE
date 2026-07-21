"""Dynasty endpoints – direct Cypher queries against the Neo4j knowledge graph."""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from app.models import (
    ChunkPreview,
    DynastyChatContext,
    DynastyDetail,
    DynastyListItem,
    DynastyListResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dynasties", tags=["dynasty"])

# ── Lazy Neo4j driver ──────────────────────────────────────────────────────────
# Initialised on first request; closed via close() in main.py lifespan teardown.

_driver = None


def _get_driver():
    global _driver
    if _driver is None:
        from neo4j import GraphDatabase
        
        uri  = os.environ["NEO4J_URI"]
        user = os.environ.get("NEO4J_USER", "neo4j")
        pwd  = os.environ["NEO4J_PASSWORD"]
        
        _driver = GraphDatabase.driver(uri, auth=(user, pwd))
        logger.info("Dynasty Neo4j driver initialised")
    return _driver


def close() -> None:
    global _driver
    if _driver is not None:
        try:
            _driver.close()
        except Exception:
            pass
        _driver = None


def _run(cypher: str, **params: Any) -> List[Dict]:
    """Execute a read query and return list of record dicts."""
    driver = _get_driver()
    with driver.session() as session:
        result = session.run(cypher, **params)
        return [dict(record) for record in result]


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("", response_model=DynastyListResponse)
async def list_dynasties() -> DynastyListResponse:
    """Return all Dynasty nodes ordered by mention count."""
    try:
        rows = await asyncio.to_thread(
            _run,
            """MATCH (d:Dynasty) 
            RETURN d.name AS name, 
                    COALESCE(d.mentions, 0) AS mentions,
                    d.period AS period,
                    d.era AS era,
                    d.capital AS capital,
                    d.description AS description,
                    d.key_figures AS key_figures,
                    d.key_events AS key_events,
                    d.start_year AS start_year
            ORDER BY COALESCE(d.start_year, 9999)
            LIMIT 50""",
        )
    except Exception as exc:
        raise HTTPException(503, f"Neo4j query failed: {exc}") from exc

    dynasties = [
        DynastyListItem(
            name        = r["name"],
            mentions    = r["mentions"],
            period      = r.get("period"),
            era         = r.get("era"),
            capital     = r.get("capital"),
            description = r.get("description"),
            key_figures = r.get("key_figures") or [],
            key_events  = r.get("key_events")  or [],
            start_year  = r.get("start_year"),
        )
        for r in rows
    ]
    return DynastyListResponse(total=len(dynasties), dynasties=dynasties)



@router.get("/{name}", response_model=DynastyDetail)
async def get_dynasty(name: str) -> DynastyDetail:
    """Return detail for one dynasty: related persons, events, places, sample chunks."""
    try:
        # Run all four queries concurrently
        base_row, persons, events, places, chunks = await asyncio.gather(
            asyncio.to_thread(
                _run,
                "MATCH (d:Dynasty {name: $name}) "
                "RETURN d.name AS name, COALESCE(d.mentions, 0) AS mentions",
                name=name,
            ),
            asyncio.to_thread(
                _run,
                "MATCH (d:Dynasty {name: $name}) "
                "MATCH (p:Person)-[:MENTIONED_IN]->(c:Chunk)-[:BELONGS_TO_DYNASTY]->(d) "
                "WHERE p.name IN d.key_figures OR any(alias IN p.aliases WHERE alias IN d.key_figures) "
                "RETURN p.name AS name, count(c) AS count "
                "ORDER BY count DESC LIMIT 10",
                name=name,
            ),
            asyncio.to_thread(
                _run,
                "MATCH (e:Event)-[:MENTIONED_IN]->(c:Chunk)-[:BELONGS_TO_DYNASTY]->(d:Dynasty) "
                "WITH e, d, count(c) AS chunk_count "
                "ORDER BY chunk_count DESC "
                "WITH e, collect({dynasty: d.name, count: chunk_count})[0] AS primary "
                "WHERE primary.dynasty = $name "
                "RETURN e.name AS name, primary.count AS count "
                "ORDER BY count DESC LIMIT 10",
                name=name,
            ),
            asyncio.to_thread(
                _run,
                "MATCH (pl:Place)-[:MENTIONED_IN]->(c:Chunk)-[:BELONGS_TO_DYNASTY]->(d:Dynasty {name: $name}) "
                "RETURN pl.name AS name, count(c) AS count "
                "ORDER BY count DESC LIMIT 10",
                name=name,
            ),
            asyncio.to_thread(
                _run,
                "MATCH (c:Chunk)-[:BELONGS_TO_DYNASTY]->(d:Dynasty {name: $name}) "
                "RETURN c.title AS title, c.text AS text "
                "ORDER BY c.chunk_id LIMIT 10",
                name=name,
            ),
        )
    except Exception as exc:
        raise HTTPException(503, f"Neo4j query failed: {exc}") from exc

    if not base_row:
        raise HTTPException(404, f"Dynasty '{name}' not found")

    filtered_persons = [r["name"] for r in persons]
    filtered_events = [r["name"] for r in events]

    # Filter places: only return places with count >= 2 (if the top place has count >= 3)
    filtered_places = []
    if places:
        max_count = places[0]["count"]
        for r in places:
            if max_count >= 3 and r["count"] < 2:
                continue
            filtered_places.append(r["name"])

    return DynastyDetail(
        name=base_row[0]["name"],
        mentions=base_row[0]["mentions"],
        persons=filtered_persons,
        events=filtered_events,
        places=filtered_places,
        sample_chunks=[
            ChunkPreview(title=r.get("title", ""), text=r.get("text", ""))
            for r in chunks
        ],
    )


@router.get("/{name}/chat-context", response_model=DynastyChatContext)
async def dynasty_chat_context(name: str) -> DynastyChatContext:
    """Return a pre-built context string ready to inject into an LLM prompt."""
    detail: DynastyDetail = await get_dynasty(name)

    lines: list[str] = [
        f"=== Dynasty: {detail.name} ===",
        f"Mentioned {detail.mentions} times in historical records.",
        "",
    ]

    if detail.persons:
        lines.append("Key Historical Figures:")
        lines.extend(f"  - {p}" for p in detail.persons)
        lines.append("")

    if detail.events:
        lines.append("Key Events:")
        lines.extend(f"  - {e}" for e in detail.events)
        lines.append("")

    if detail.places:
        lines.append("Key Places:")
        lines.extend(f"  - {pl}" for pl in detail.places)
        lines.append("")

    if detail.sample_chunks:
        lines.append("Sample Historical Passages:")
        for chunk in detail.sample_chunks:
            snippet = chunk.text[:300].rstrip()
            if len(chunk.text) > 300:
                snippet += " …"
            lines.append(f"[{chunk.title}]:")
            lines.append(snippet)
            lines.append("---")

    return DynastyChatContext(name=detail.name, context="\n".join(lines))
