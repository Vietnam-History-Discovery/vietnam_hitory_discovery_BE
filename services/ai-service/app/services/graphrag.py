"""Singleton wrappers around EmbeddingStore + GraphExpander + ClaudeGenerator.

Loaded once at startup via load() and reused across all requests.
"""
from __future__ import annotations
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Module-level singletons – populated by load()
_embed_store = None
_graph_expander = None
_llm = None
_chunks_count: int = 0
_neo4j_ok: bool = False
_ready: bool = False


def load() -> None:
    """Import src modules and initialise all shared components."""
    global _embed_store, _graph_expander, _llm, _chunks_count, _neo4j_ok, _ready

    # src path is inserted by main.py before this module is imported
    from graphrag_retriever import (  # type: ignore[import]
        EmbeddingStore,
        GraphExpander,
        ClaudeGenerator,
    )

    logger.info("Loading EmbeddingStore …")
    _embed_store = EmbeddingStore()
    _embed_store.build()
    _chunks_count = len(getattr(_embed_store, "chunks", []) or [])
    logger.info("EmbeddingStore ready – %d chunks loaded", _chunks_count)

    logger.info("Connecting GraphExpander to Neo4j …")
    try:
        _graph_expander = GraphExpander()
        _neo4j_ok = True
        logger.info("Neo4j connected")
    except Exception as exc:
        logger.error("Neo4j connection failed: %s", exc)
        _neo4j_ok = False

    logger.info("Initialising LLM …")
    _llm = ClaudeGenerator()

    _ready = True


def close() -> None:
    global _graph_expander, _ready
    if _graph_expander is not None:
        try:
            _graph_expander.close()
        except Exception:
            pass
    _ready = False


def is_ready() -> bool:
    return _ready


def neo4j_connected() -> bool:
    return _neo4j_ok


def chunks_loaded() -> int:
    return _chunks_count


# ── Query helpers ──────────────────────────────────────────────────────────────

def query_graph(question: str, top_k: int = 10) -> dict:
    """GraphRAG query: vector search → graph expansion → LLM generation."""
    from graphrag_retriever import build_context, extract_entity  # type: ignore[import]

    if not _ready:
        raise RuntimeError("GraphRAG not initialised")

    # Strip context prefix [dynasty_name] nếu có
    dynasty_context: Optional[str] = None
    clean_question = question
    if question.startswith("[") and "]" in question:
        end = question.index("]")
        dynasty_context = question[1:end].strip()
        clean_question = question[end + 1:].strip()
        logger.info("Dynasty context: '%s' | Clean question: '%s'", dynasty_context, clean_question)

    # Entity lookup for definition-style queries ("là ai", "là gì", bare noun phrases)
    entity_info = None
    entity = extract_entity(clean_question)
    if entity and _neo4j_ok and _graph_expander is not None:
        try:
            entity_info = _graph_expander.lookup_entity(entity)
            if entity_info:
                logger.info(
                    "Entity node found: %s [%s] — %d title-matched chunks",
                    entity_info.get("name"),
                    entity_info.get("type"),
                    len(entity_info.get("context_chunks") or []),
                )
            else:
                logger.info("No entity node found for: '%s'", entity)
        except Exception as exc:
            logger.warning("Entity lookup failed: %s", exc)

    # Fallback: when clean_question yields no entity, try the dynasty_context
    # (handles edge cases where the prefix IS the entity, e.g. [Hùng Vương] <empty>)
    if entity_info is None and dynasty_context and _neo4j_ok and _graph_expander is not None:
        try:
            entity_info = _graph_expander.lookup_entity(dynasty_context)
            if entity_info:
                logger.info(
                    "Dynasty-context entity found: %s [%s]",
                    entity_info.get("name"),
                    entity_info.get("type"),
                )
        except Exception as exc:
            logger.warning("Dynasty context entity lookup failed: %s", exc)

    chunks = _embed_store.search(clean_question, top_k=top_k, dynasty_context=dynasty_context)

    logger.info("Retrieved %d chunks", len(chunks))
    for i, c in enumerate(chunks, 1):
        logger.info(
            "[%d] score=%.3f | %s",
            i,
            c.get("score", 0),
            c.get("title", "NO_TITLE"),
        )
        logger.info("TEXT: %s", c.get("text", "")[:200].replace("\n", " "))

    chunk_ids = [c.get("chunk_id", c.get("id", "")) for c in chunks]

    graph_data: dict = {}
    if _neo4j_ok and _graph_expander is not None:
        try:
            graph_data = _graph_expander.expand(chunk_ids)
        except Exception as exc:
            logger.warning("Graph expansion failed: %s", exc)

    context_str = build_context(clean_question, chunks, graph_data, entity_info=entity_info)
    print("\n===== FULL CONTEXT =====\n")
    print(context_str[:5000])
    print("\n========================\n")

    # Thêm dynasty context vào đầu prompt nếu có
    if dynasty_context:
        context_str = f"## Triều đại đang xem: {dynasty_context}\n\n" + context_str

    answer = _llm.generate(clean_question, context_str)

    entities: list = graph_data.get("entities", [])
    graph_nodes = (
        len(graph_data.get("nodes", []))
        or len(graph_data.get("graph_context", []))
        or len(entities)
    )

    return {
        "answer": answer,
        "chunks_used": len(chunks),
        "entities": entities if isinstance(entities, list) else list(entities),
        "graph_nodes": graph_nodes,
    }


def query_naive(question: str, top_k: int = 10) -> dict:
    """Naive (vector-only) RAG query."""
    from evaluator import NaiveRAG  # type: ignore[import]

    if not _ready:
        raise RuntimeError("GraphRAG not initialised")

    naive = NaiveRAG(_embed_store, _llm)
    answer, chunks = naive.query(question, top_k=top_k)

    return {
        "answer": answer,
        "chunks_used": len(chunks) if chunks else 0,
    }
