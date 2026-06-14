"""FastAPI entry-point for the Vietnamese History GraphRAG AI service.

sys.path is extended here – before any local imports – so that the shared
src/ packages (graphrag_retriever, evaluator, graph_builder, etc.) are
importable without installing them as packages.
"""
from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# ── Path setup (must come before any src imports) ──────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
for _p in [
    _PROJECT_ROOT / "src",
    _PROJECT_ROOT / "src" / "graph",
    _PROJECT_ROOT / "src" / "parsers",
    _PROJECT_ROOT / "src" / "crawlers",
]:
    _sp = str(_p)
    if _sp not in sys.path:
        sys.path.insert(0, _sp)
# ────────────────────────────────────────────────────────────────────────────────

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.models import HealthResponse
from app.routers import dynasty, eval, ingest, query
from app.services import graphrag as graphrag_svc

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s – %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting AI service – loading GraphRAG components …")
    try:
        graphrag_svc.load()
        logger.info("GraphRAG components loaded successfully")
    except Exception as exc:
        logger.error("GraphRAG startup failed (service will run degraded): %s", exc)
    yield
    logger.info("Shutting down AI service …")
    graphrag_svc.close()
    dynasty.close()


app = FastAPI(
    title="Vietnamese History GraphRAG – AI Service",
    description="Query, ingestion, and evaluation endpoints for the GraphRAG pipeline.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(query.router)
app.include_router(ingest.router)
app.include_router(eval.router)
app.include_router(dynasty.router, prefix="/api")


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health() -> HealthResponse:
    """Service health check."""
    ok = graphrag_svc.is_ready()
    return HealthResponse(
        status="healthy" if ok else "degraded",
        neo4j_connected=graphrag_svc.neo4j_connected(),
        chunks_loaded=graphrag_svc.chunks_loaded(),
    )
