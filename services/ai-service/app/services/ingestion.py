"""Background ingestion pipeline: crawl → parse → NER → graph build."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

_status: dict = {
    "job_id": None,
    "status": "idle",
    "phase": None,
    "message": "No ingestion job has been run yet.",
    "started_at": None,
    "completed_at": None,
}


def get_status() -> dict:
    return dict(_status)


def start_ingest(delay: float = 2.0) -> str:
    if _status["status"] == "running":
        raise RuntimeError("An ingestion job is already running")

    job_id = str(uuid.uuid4())
    _status.update(
        job_id=job_id,
        status="running",
        phase="crawl",
        message="Ingestion started",
        started_at=datetime.now(timezone.utc).isoformat(),
        completed_at=None,
    )
    return job_id


def run_full_ingest(job_id: str, delay: float = 2.0) -> None:
    """Runs all four pipeline phases synchronously (called from a background thread)."""

    def _set(phase: str, message: str) -> None:
        _status.update(phase=phase, message=message)
        logger.info("[ingest %s] phase=%s – %s", job_id[:8], phase, message)

    try:
        # ── Phase 1: Crawl ─────────────────────────────────────────────────────
        _set("crawl", "Crawling ĐVSKTT from Wikisource …")
        from dvsktt_crawler import DVSKTTCrawler  # type: ignore[import]

        crawler = DVSKTTCrawler(delay=delay)
        pages = crawler.crawl_all()
        _set("crawl", f"Crawled {len(pages)} pages")

        # ── Phase 2: Parse ─────────────────────────────────────────────────────
        _set("parse", "Parsing and chunking raw text …")
        from text_cleaner import ParsePipeline  # type: ignore[import]

        parse_pipeline = ParsePipeline()
        chunks = parse_pipeline.process_dvsktt()
        _set("parse", f"Parsed {len(chunks)} chunks")

        # ── Phase 3: NER & relations ───────────────────────────────────────────
        _set("ner", "Extracting entities and relations …")
        from ner_extractor import NERPipeline  # type: ignore[import]

        ner_pipeline = NERPipeline()
        records = ner_pipeline.process(chunks_path=None)
        _set("ner", f"Extracted entities for {len(records)} chunks")

        # ── Phase 4: Graph build ───────────────────────────────────────────────
        _set("graph", "Importing data into Neo4j …")
        from graph_builder import build_graph  # type: ignore[import]

        build_graph()
        _set("graph", "Graph build complete")

        _status.update(
            status="completed",
            message="Full ingestion pipeline completed successfully",
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
        logger.info("[ingest %s] completed", job_id[:8])

    except Exception as exc:
        logger.exception("[ingest %s] failed: %s", job_id[:8], exc)
        _status.update(
            status="failed",
            message=f"Ingestion failed during '{_status.get('phase')}' phase: {exc}",
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
