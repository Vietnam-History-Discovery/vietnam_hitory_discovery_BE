from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.models import IngestRequest, IngestStatusResponse
from app.services import ingestion as ingest_svc

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("/full", response_model=IngestStatusResponse, status_code=202)
async def start_full_ingest(
    req: IngestRequest, background_tasks: BackgroundTasks
) -> IngestStatusResponse:
    """Start the full ingestion pipeline in the background.

    Phases: crawl → parse → NER → graph build.
    Poll GET /ingest/status to track progress.
    """
    try:
        job_id = ingest_svc.start_ingest(delay=req.delay)
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc

    background_tasks.add_task(ingest_svc.run_full_ingest, job_id, req.delay)

    return IngestStatusResponse(**ingest_svc.get_status())


@router.get("/status", response_model=IngestStatusResponse)
async def ingest_status() -> IngestStatusResponse:
    """Return the current ingestion job status."""
    return IngestStatusResponse(**ingest_svc.get_status())
