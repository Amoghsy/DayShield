"""Analysis endpoints for DayShield (Phase 1)."""

from __future__ import annotations

import uuid
from fastapi import APIRouter, HTTPException, status

from app.agents.workflow import run_analysis_workflow
from app.api.schemas.analysis import AnalysisResultResponse, AnalysisStartRequest

router = APIRouter(prefix="/api/analysis", tags=["Analysis"])

# In-memory store for Phase 1; replaced by SQLite/SQLAlchemy in Phase 4.
_ANALYSES_STORE: dict[str, AnalysisResultResponse] = {}


@router.post(
    "/start",
    response_model=AnalysisResultResponse,
    status_code=status.HTTP_200_OK,
    summary="Start multi-agent commute disruption analysis",
)
async def start_analysis(request: AnalysisStartRequest) -> AnalysisResultResponse:
    """Run the 4-agent DayShield ADK workflow for the given commute context."""
    analysis_id = str(uuid.uuid4())
    result = await run_analysis_workflow(request, analysis_id=analysis_id)
    _ANALYSES_STORE[analysis_id] = result
    if result.status == "failed":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.error or "Workflow execution failed.",
        )
    return result


@router.get(
    "/{analysis_id}",
    response_model=AnalysisResultResponse,
    summary="Retrieve a completed or failed analysis by ID",
)
async def get_analysis(analysis_id: str) -> AnalysisResultResponse:
    """Fetch a previously executed analysis result."""
    result = _ANALYSES_STORE.get(analysis_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis '{analysis_id}' not found.",
        )
    return result
