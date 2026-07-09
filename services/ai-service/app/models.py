from __future__ import annotations

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


# ── Query ──────────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=50000)
    top_k: int = Field(10, ge=1, le=20)


class QueryResponse(BaseModel):
    answer: str
    chunks_used: int
    entities: List[str]
    graph_nodes: int


class NaiveQueryResponse(BaseModel):
    answer: str
    chunks_used: int


# ── Ingest ─────────────────────────────────────────────────────────────────────

class IngestRequest(BaseModel):
    delay: float = Field(2.0, ge=0.5, le=10.0, description="Crawl delay in seconds")


class IngestStatusResponse(BaseModel):
    job_id: Optional[str] = None
    status: str  # idle | running | completed | failed
    phase: Optional[str] = None  # crawl | parse | ner | graph
    message: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


# ── Eval ───────────────────────────────────────────────────────────────────────

class EvalRunRequest(BaseModel):
    sample_size: int = Field(25, ge=1, le=25)


class EvalJobResponse(BaseModel):
    job_id: str
    status: str
    message: str


class EvalResultItem(BaseModel):
    id: str
    question: str
    category: str
    naive_answer: str
    graph_answer: str
    naive_scores: Dict[str, float]
    graph_scores: Dict[str, float]
    graph_entities: int
    graph_relations: int


class EvalSummaryResponse(BaseModel):
    status: str  # idle | running | completed | failed
    total_evaluated: int
    naive_avg: Dict[str, float]
    graph_avg: Dict[str, float]
    improvement: Dict[str, float]


class EvalResultsResponse(BaseModel):
    total: int
    results: List[EvalResultItem]


# ── Dynasty ────────────────────────────────────────────────────────────────────

class DynastyListItem(BaseModel):
    name:         str
    mentions:     int
    period:       Optional[str] = None
    era:          Optional[str] = None
    capital:      Optional[str] = None
    description:  Optional[str] = None
    key_figures:  List[str] = []
    key_events:   List[str] = []
    start_year:   Optional[int] = None


class ChunkPreview(BaseModel):
    title: str
    text: str


class DynastyDetail(BaseModel):
    name: str
    mentions: int
    persons: List[str]
    events: List[str]
    places: List[str]
    sample_chunks: List[ChunkPreview]


class DynastyChatContext(BaseModel):
    name: str
    context: str


class DynastyListResponse(BaseModel):
    total:     int
    dynasties: List[DynastyListItem]


# ── Health ─────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str  # healthy | degraded
    neo4j_connected: bool
    chunks_loaded: int
    service: str = "ai-service"
    version: str = "1.0.0"
