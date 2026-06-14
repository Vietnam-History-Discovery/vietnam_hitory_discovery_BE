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

def query_graph(question: str, top_k: int = 5) -> dict:
    """GraphRAG query: vector search → graph expansion → LLM generation."""
    from graphrag_retriever import build_context  # type: ignore[import]

    if not _ready:
        raise RuntimeError("GraphRAG not initialised")

    # Strip context prefix [dynasty_name] nếu có
    # Ví dụ: "[nhà Triệu] Triệu Đà là ai?" → dynasty_context="nhà Triệu", clean_question="Triệu Đà là ai?"
    dynasty_context: Optional[str] = None
    clean_question = question
    if question.startswith("[") and "]" in question:
        end = question.index("]")
        dynasty_context = question[1:end].strip()
        clean_question = question[end + 1:].strip()
        logger.info("Dynasty context: '%s' | Clean question: '%s'", dynasty_context, clean_question)

    # Dùng clean_question cho vector search để tránh embedding bị lệch
    chunks = _embed_store.search(clean_question, top_k=top_k)
    chunk_ids = [c.get("chunk_id", c.get("id", "")) for c in chunks]

    graph_data: dict = {}
    if _neo4j_ok and _graph_expander is not None:
        try:
            graph_data = _graph_expander.expand(chunk_ids)
        except Exception as exc:
            logger.warning("Graph expansion failed: %s", exc)

    context_str = build_context(clean_question, chunks, graph_data)

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


def query_naive(question: str, top_k: int = 5) -> dict:
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
