"""Analysis endpoints for DayShield (persisted to SQLite)."""

from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.agents.workflow import run_analysis_workflow
from app.api.schemas.analysis import AnalysisResultResponse, AnalysisStartRequest
from app.database.database import get_db
from app.database.models import Analysis
from app.services.analysis_service import execute_and_persist_analysis

router = APIRouter(prefix="/api/analysis", tags=["Analysis"])


@router.post(
    "/start",
    response_model=AnalysisResultResponse,
    status_code=status.HTTP_200_OK,
    summary="Start multi-agent commute disruption analysis",
)
async def start_analysis(
    request: AnalysisStartRequest,
    db: Session = Depends(get_db),
) -> AnalysisResultResponse:
    """Run the 4-agent DayShield ADK workflow, validate actions, and persist to SQLite."""
    analysis_id = str(uuid.uuid4())
    result = await execute_and_persist_analysis(
        db,
        request,
        analysis_id=analysis_id,
        workflow_runner=run_analysis_workflow,
    )
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
async def get_analysis(
    analysis_id: str,
    db: Session = Depends(get_db),
) -> AnalysisResultResponse:
    """Fetch a previously executed analysis result from SQLite."""
    row = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis '{analysis_id}' not found.",
        )
    return AnalysisResultResponse(
        analysis_id=row.id,
        status=row.status,  # type: ignore[arg-type]
        simulation_mode=row.simulation_mode,
        created_at=row.created_at,
        commute_assessment=row.commute_assessment,
        schedule_assessment=row.schedule_assessment,
        priority_assessment=row.priority_assessment,
        recovery_plan=row.recovery_plan,
        error=row.error,
    )
