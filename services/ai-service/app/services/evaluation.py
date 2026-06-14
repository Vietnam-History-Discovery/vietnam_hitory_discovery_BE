"""Background evaluation runner wrapping evaluator.run_evaluation()."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional

logger = logging.getLogger(__name__)

_status: dict = {
    "job_id": None,
    "status": "idle",
    "message": "No evaluation job has been run yet.",
    "started_at": None,
    "completed_at": None,
}
_results: Optional[List] = None  # list[EvalResult] from evaluator


def get_status() -> dict:
    return dict(_status)


def get_summary() -> dict:
    if _results is None:
        return {
            "status": _status["status"],
            "total_evaluated": 0,
            "naive_avg": {},
            "graph_avg": {},
            "improvement": {},
        }

    def _avg(key: str, score_field: str) -> float:
        vals = [
            getattr(r, score_field, {}).get(key, None)
            for r in _results
            if getattr(r, score_field, {}).get(key) is not None
        ]
        return round(sum(vals) / len(vals), 4) if vals else 0.0

    metrics = ["answer_relevancy", "faithfulness", "context_recall"]
    naive_avg = {m: _avg(m, "naive_scores") for m in metrics}
    graph_avg = {m: _avg(m, "graph_scores") for m in metrics}
    improvement = {m: round(graph_avg[m] - naive_avg[m], 4) for m in metrics}

    return {
        "status": _status["status"],
        "total_evaluated": len(_results),
        "naive_avg": naive_avg,
        "graph_avg": graph_avg,
        "improvement": improvement,
    }


def get_results() -> List[dict]:
    if _results is None:
        return []

    out = []
    for r in _results:
        out.append(
            {
                "id": getattr(r, "id", ""),
                "question": getattr(r, "question", ""),
                "category": getattr(r, "category", ""),
                "naive_answer": getattr(r, "naive_answer", ""),
                "graph_answer": getattr(r, "graph_answer", ""),
                "naive_scores": getattr(r, "naive_scores", {}),
                "graph_scores": getattr(r, "graph_scores", {}),
                "graph_entities": getattr(r, "graph_entities", 0),
                "graph_relations": getattr(r, "graph_relations", 0),
            }
        )
    return out


def start_eval(sample_size: int = 25) -> str:
    if _status["status"] == "running":
        raise RuntimeError("An evaluation job is already running")

    job_id = str(uuid.uuid4())
    _status.update(
        job_id=job_id,
        status="running",
        message=f"Evaluation started (sample_size={sample_size})",
        started_at=datetime.now(timezone.utc).isoformat(),
        completed_at=None,
    )
    return job_id


def run_evaluation_job(job_id: str, sample_size: int = 25) -> None:
    """Runs evaluation synchronously (called from a background thread)."""
    global _results

    logger.info("[eval %s] starting – sample_size=%d", job_id[:8], sample_size)
    try:
        from evaluator import run_evaluation  # type: ignore[import]

        _results = run_evaluation(sample_size=sample_size)

        _status.update(
            status="completed",
            message=f"Evaluation completed – {len(_results)} questions scored",
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
        logger.info("[eval %s] completed – %d results", job_id[:8], len(_results))

    except Exception as exc:
        logger.exception("[eval %s] failed: %s", job_id[:8], exc)
        _status.update(
            status="failed",
            message=f"Evaluation failed: {exc}",
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
