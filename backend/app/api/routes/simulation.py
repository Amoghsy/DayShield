"""Simulation endpoints for reliable hackathon demonstrations (Scenarios A, B, C)."""

from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.workflow import run_analysis_workflow
from app.api.schemas.analysis import AnalysisResultResponse
from app.database.database import get_db
from app.services.analysis_service import execute_and_persist_analysis
from app.services.simulation_service import build_simulation_request

router = APIRouter(prefix="/api/simulation", tags=["Simulation"])


class SimulationRunRequest(BaseModel):
    """Request body for running a named simulation scenario."""

    scenario: Literal["scenario_a", "scenario_b", "scenario_c"] = "scenario_a"


@router.post(
    "/run",
    response_model=AnalysisResultResponse,
    status_code=status.HTTP_200_OK,
    summary="Run a preconfigured simulation scenario (A, B, or C)",
)
async def run_simulation(
    body: SimulationRunRequest | None = None,
    scenario: Literal["scenario_a", "scenario_b", "scenario_c"] | None = Query(
        default=None, description="Optional scenario query override"
    ),
    db: Session = Depends(get_db),
) -> AnalysisResultResponse:
    """Execute DayShield in clearly labeled simulation mode for Scenario A, B, or C."""
    chosen = scenario or (body.scenario if body else "scenario_a")
    req = build_simulation_request(chosen)
    analysis_id = str(uuid.uuid4())
    result = await execute_and_persist_analysis(
        db,
        req,
        analysis_id=analysis_id,
        workflow_runner=run_analysis_workflow,
    )
    if result.status == "failed":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.error or "Simulation workflow failed.",
        )
    return result
