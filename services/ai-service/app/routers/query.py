from fastapi import APIRouter, HTTPException

from app.models import (
    NaiveQueryResponse,
    QueryRequest,
    QueryResponse,
    TimelineQueryRequest,
)
from app.services import graphrag as graphrag_svc
from app.services.sse import sse_response

router = APIRouter(prefix="/query", tags=["query"])


@router.post("", response_model=QueryResponse)
async def query_graph(req: QueryRequest) -> QueryResponse:
    """GraphRAG query: vector search + graph expansion + LLM generation."""
    if not graphrag_svc.is_ready():
        raise HTTPException(503, "GraphRAG service is not ready yet")
    try:
        result = graphrag_svc.query_graph(req.question, top_k=req.top_k)
        return QueryResponse(**result)
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc


@router.post("/stream")
async def query_graph_stream(req: QueryRequest):
    """Streaming counterpart of POST /query — SSE frames: meta -> delta* -> done."""
    if not graphrag_svc.is_ready():
        raise HTTPException(503, "GraphRAG service is not ready yet")
    return sse_response(graphrag_svc.query_graph_stream(req.question, top_k=req.top_k))


@router.post("/naive", response_model=NaiveQueryResponse)
async def query_naive(req: QueryRequest) -> NaiveQueryResponse:
    """Naive (vector-only) RAG query – baseline without graph expansion."""
    if not graphrag_svc.is_ready():
        raise HTTPException(503, "GraphRAG service is not ready yet")
    try:
        result = graphrag_svc.query_naive(req.question, top_k=req.top_k)
        return NaiveQueryResponse(**result)
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc


@router.post("/timeline/stream")
async def query_timeline_stream(req: TimelineQueryRequest):
    if not graphrag_svc.is_ready():
        raise HTTPException(503, "GraphRAG service is not ready yet")
    return sse_response(graphrag_svc.query_timeline_stream(
        question=req.question,
        context=req.context,
        current_snapshot=req.current_snapshot.model_dump() if req.current_snapshot else None,
        recent_exchanges=req.recent_exchanges,
    ))
