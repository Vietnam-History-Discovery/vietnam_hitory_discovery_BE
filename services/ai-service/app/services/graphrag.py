"""Singleton wrappers around EmbeddingStore + GraphExpander + ClaudeGenerator.

Loaded once at startup via load() and reused across all requests.
"""
from __future__ import annotations
import json
import logging
import os
import uuid
from typing import Optional

from pydantic import ValidationError

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

def _retrieve(question: str, context_override: Optional[str] = None, top_k: int = 10) -> dict:
    """Shared retrieval pipeline: dynasty-prefix stripping → entity lookup →
    vector search → graph expansion → context string. Used by both
    query_graph and query_timeline so the two stay in sync."""
    from graphrag_retriever import build_context, extract_entity  # type: ignore[import]

    # Strip context prefix [dynasty_name] nếu có
    dynasty_context: Optional[str] = None
    clean_question = question
    if question.startswith("[") and "]" in question:
        end = question.index("]")
        dynasty_context = question[1:end].strip()
        clean_question = question[end + 1:].strip()
        logger.info("Dynasty context: '%s' | Clean question: '%s'", dynasty_context, clean_question)

    if context_override:
        dynasty_context = context_override

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
    if dynasty_context:
        context_str = f"## Triều đại đang xem: {dynasty_context}\n\n" + context_str

    return {
        "clean_question": clean_question,
        "dynasty_context": dynasty_context,
        "chunks": chunks,
        "graph_data": graph_data,
        "context_str": context_str,
    }


def query_graph(question: str, top_k: int = 10) -> dict:
    """GraphRAG query: vector search → graph expansion → LLM generation."""
    if not _ready:
        raise RuntimeError("GraphRAG not initialised")

    retrieval = _retrieve(question, top_k=top_k)
    context_str = retrieval["context_str"]

    print("\n===== FULL CONTEXT =====\n")
    print(context_str[:5000])
    print("\n========================\n")

    answer = _llm.generate(retrieval["clean_question"], context_str)

    graph_data = retrieval["graph_data"]
    entities: list = graph_data.get("entities", [])
    graph_nodes = (
        len(graph_data.get("nodes", []))
        or len(graph_data.get("graph_context", []))
        or len(entities)
    )

    return {
        "answer": answer,
        "chunks_used": len(retrieval["chunks"]),
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


# ── Timeline generation ──────────────────────────────────────────────────────

_TIMELINE_MODEL = os.getenv("TIMELINE_MODEL", "openai/gpt-oss-120b")
_TIMELINE_CONTEXT_CHAR_LIMIT = int(os.getenv("TIMELINE_CONTEXT_CHAR_LIMIT", "4000"))

_TIMELINE_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "answer": {"type": "string"},
        "events": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "dateLabel": {"type": "string"},
                    "start_year": {"type": ["integer", "null"]},
                    "end_year": {"type": ["integer", "null"]},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "related_entities": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["id", "dateLabel", "start_year", "end_year", "title", "description", "related_entities"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["title", "answer", "events"],
    "additionalProperties": False,
}

_TIMELINE_SYSTEM_PROMPT = """Bạn là chuyên gia lịch sử Việt Nam. Dựa vào nội dung lịch sử được cung cấp, hãy tạo một dòng thời gian (timeline) gồm các sự kiện chính.

Yêu cầu:
- Trả về JSON đúng schema với title (tiêu đề timeline), answer (câu trả lời) và events (mảng sự kiện)
- answer là một câu trả lời ngắn gọn, tự nhiên bằng tiếng Việt, trả lời trực tiếp câu hỏi của người dùng và có thể nêu vài điểm nổi bật của dòng thời gian. Đây KHÔNG phải là tiêu đề, mà là một câu trả lời hội thoại thực sự.
- Mỗi sự kiện có: id (duy nhất), dateLabel (nhãn hiển thị, VD: "Thế kỷ X", "Năm 179 TCN", "Khoảng năm 40"), start_year (năm bắt đầu bằng số, BCE là số âm), end_year (năm kết thúc bằng số, có thể null), title (tiêu đề), description (mô tả), related_entities (các thực thể liên quan)
- Sắp xếp sự kiện theo thứ tự thời gian tăng dần (start_year nếu có, nếu không thì dùng dateLabel)
- LUÔN tạo ít nhất 3-5 sự kiện dựa vào kiến thức lịch sử của bạn khi câu hỏi liên quan đến lịch sử Việt Nam.
- Nếu câu hỏi KHÔNG liên quan đến lịch sử Việt Nam, hoặc bạn không có đủ thông tin để tạo dòng thời gian, hãy trả về events là mảng rỗng ([]), và answer/title có thể để trống — hệ thống sẽ tự thay thế bằng một câu trả lời phù hợp cho người dùng trong trường hợp này.
- Nội dung bằng tiếng Việt
- Tối đa 20 sự kiện"""

_TIMELINE_FALLBACK_ANSWER = (
    "Xin lỗi, tôi không thể tạo dòng thời gian cho câu hỏi này. Bạn có thể hỏi tôi về "
    "những chủ đề liên quan đến lịch sử, sự kiện và dòng thời gian Việt Nam, ví dụ như "
    "nhà Nguyễn, nhà Trần, Hai Bà Trưng, thời kỳ Bắc thuộc, v.v."
)


def _timeline_fallback(chunks: list, graph_data: dict) -> dict:
    """Response used when the model can't produce a usable timeline (off-topic
    question, malformed/empty output) — a normal chat-style answer instead of
    an error, so the UI doesn't have to treat it as a failure."""
    entities = graph_data.get("entities", [])
    graph_nodes_val = (
        len(graph_data.get("nodes", []))
        or len(graph_data.get("graph_context", []))
        or len(entities)
    )
    return {
        "answer": _TIMELINE_FALLBACK_ANSWER,
        "timeline": None,
        "chunks_used": len(chunks),
        "entities": entities if isinstance(entities, list) else list(entities),
        "graph_nodes": graph_nodes_val,
    }


def query_timeline(
    question: str,
    context: Optional[str] = None,
    current_snapshot: Optional[dict] = None,
    recent_exchanges: Optional[list[dict]] = None,
) -> dict:
    """Generate a timeline snapshot using GraphRAG retrieval + Groq JSON Schema."""
    if not _ready:
        raise RuntimeError("GraphRAG not initialised")

    retrieval = _retrieve(question, context_override=context, top_k=10)
    clean_question = retrieval["clean_question"]
    context_str = retrieval["context_str"]
    graph_data = retrieval["graph_data"]
    chunks = retrieval["chunks"]

    if len(context_str) > _TIMELINE_CONTEXT_CHAR_LIMIT:
        logger.info(
            "Timeline context truncated: %d -> %d chars",
            len(context_str), _TIMELINE_CONTEXT_CHAR_LIMIT,
        )
        context_str = context_str[:_TIMELINE_CONTEXT_CHAR_LIMIT] + "\n… (nội dung đã rút gọn)"

    user_prompt_parts = [f"Câu hỏi: {clean_question}\n\nThông tin lịch sử:\n{context_str}"]

    if current_snapshot:
        user_prompt_parts.append(
            f"\n\nTimeline hiện tại:\nTiêu đề: {current_snapshot.get('title', '')}\n"
            f"Số sự kiện: {len(current_snapshot.get('events', []))}"
        )

    if recent_exchanges:
        user_prompt_parts.append("\n\nLịch sử hội thoại gần đây:")
        for i, ex in enumerate(recent_exchanges[-3:], 1):
            user = ex.get("user", "")
            assistant = ex.get("assistant", "")
            if user:
                user_prompt_parts.append(f"[Lần {i}] Người dùng: {user}")
            if assistant:
                user_prompt_parts.append(f"[Lần {i}] Trợ lý: {assistant[:200]}")

    user_prompt = "\n".join(user_prompt_parts)

    try:
        raw = _llm.generate_structured(
            system_prompt=_TIMELINE_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            schema=_TIMELINE_JSON_SCHEMA,
            schema_name="timeline_snapshot",
            model=_TIMELINE_MODEL,
        )

        timeline_data = json.loads(raw)
        answer_text = (timeline_data.pop("answer", "") or "").strip()
        from app.models import TimelineSnapshot

        snapshot = TimelineSnapshot(**timeline_data)

        if not snapshot.events:
            return _timeline_fallback(chunks, graph_data)

        snapshot.events.sort(
            key=lambda e: (
                e.start_year if e.start_year is not None
                else (e.end_year if e.end_year is not None else 9999)
            )
        )

        if not snapshot.id:
            snapshot.id = str(uuid.uuid4())

        entities = graph_data.get("entities", [])
        graph_nodes_val = (
            len(graph_data.get("nodes", []))
            or len(graph_data.get("graph_context", []))
            or len(entities)
        )

        return {
            "answer": answer_text or f"**{snapshot.title}** - {len(snapshot.events)} sự kiện lịch sử",
            "timeline": snapshot.model_dump(),
            "chunks_used": len(chunks),
            "entities": entities if isinstance(entities, list) else list(entities),
            "graph_nodes": graph_nodes_val,
        }

    except (json.JSONDecodeError, ValidationError) as exc:
        logger.warning("Timeline generation produced unusable output, falling back: %s", exc)
        return _timeline_fallback(chunks, graph_data)
    except Exception as exc:
        logger.error("Timeline generation failed: %s", exc)
        raise RuntimeError(f"Timeline generation failed: {exc}")
