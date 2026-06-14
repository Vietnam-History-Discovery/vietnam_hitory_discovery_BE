from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.models import (
    EvalJobResponse,
    EvalResultsResponse,
    EvalRunRequest,
    EvalSummaryResponse,
)
from app.services import evaluation as eval_svc

router = APIRouter(prefix="/eval", tags=["eval"])


@router.post("/run", response_model=EvalJobResponse, status_code=202)
async def run_eval(
    req: EvalRunRequest, background_tasks: BackgroundTasks
) -> EvalJobResponse:
    """Start an evaluation job comparing GraphRAG vs Naive RAG.

    Poll GET /eval/summary to track progress and see results.
    """
    try:
        job_id = eval_svc.start_eval(sample_size=req.sample_size)
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc

    background_tasks.add_task(eval_svc.run_evaluation_job, job_id, req.sample_size)

    return EvalJobResponse(
        job_id=job_id,
        status="running",
        message=f"Evaluation started with sample_size={req.sample_size}",
    )


@router.get("/summary", response_model=EvalSummaryResponse)
async def eval_summary() -> EvalSummaryResponse:
    """Return aggregated metrics from the last completed evaluation."""
    return EvalSummaryResponse(**eval_svc.get_summary())


@router.get("/results", response_model=EvalResultsResponse)
async def eval_results() -> EvalResultsResponse:
    """Return per-question results from the last completed evaluation."""
    results = eval_svc.get_results()
    return EvalResultsResponse(total=len(results), results=results)
