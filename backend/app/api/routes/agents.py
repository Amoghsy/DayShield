"""Agent execution status and Server-Sent Events (SSE) streaming endpoints."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import AgentExecutionLog, Analysis

router = APIRouter(prefix="/api/agents", tags=["Agents & Streaming"])

PIPELINE_AGENTS = [
    "commute_agent",
    "schedule_agent",
    "impact_merge",
    "priority_agent",
    "recovery_agent",
]


@router.get(
    "/status/{analysis_id}",
    summary="Get execution status of each agent for an analysis",
)
async def get_agent_status(
    analysis_id: str,
    db: Session = Depends(get_db),
) -> dict:
    """Return per-agent execution state (pending, completed, failed) for an analysis."""
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis '{analysis_id}' not found.",
        )

    logs = (
        db.query(AgentExecutionLog)
        .filter(AgentExecutionLog.analysis_id == analysis_id)
        .order_by(AgentExecutionLog.created_at.asc())
        .all()
    )
    logged_map: dict[str, str] = {}
    for log in logs:
        logged_map[log.agent_name] = log.status

    agent_states = []
    for name in PIPELINE_AGENTS:
        if name in logged_map:
            state = logged_map[name]
        elif analysis.status == "completed":
            state = "completed"
        elif analysis.status == "failed":
            state = "failed"
        else:
            state = "pending"
        agent_states.append({"agent": name, "status": state})

    return {
        "analysis_id": analysis_id,
        "overall_status": analysis.status,
        "simulation_mode": analysis.simulation_mode,
        "agents": agent_states,
    }


@router.get(
    "/stream/{analysis_id}",
    summary="Stream agent execution status updates via Server-Sent Events (SSE)",
)
async def stream_agent_status(
    analysis_id: str,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Emit SSE events for each agent's status in the DayShield workflow."""
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis '{analysis_id}' not found.",
        )

    logs = (
        db.query(AgentExecutionLog)
        .filter(AgentExecutionLog.analysis_id == analysis_id)
        .order_by(AgentExecutionLog.created_at.asc())
        .all()
    )

    async def event_generator() -> AsyncGenerator[str, None]:
        for name in PIPELINE_AGENTS:
            matched = [l for l in logs if l.agent_name == name]
            status_val = matched[-1].status if matched else (
                "completed" if analysis.status == "completed" else analysis.status
            )
            payload = {
                "analysis_id": analysis_id,
                "agent": name,
                "status": status_val,
                "simulation_mode": analysis.simulation_mode,
            }
            yield f"event: agent_update\ndata: {json.dumps(payload)}\n\n"
            await asyncio.sleep(0.01)

        done_payload = {
            "analysis_id": analysis_id,
            "overall_status": analysis.status,
        }
        yield f"event: complete\ndata: {json.dumps(done_payload)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
