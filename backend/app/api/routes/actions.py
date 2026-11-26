"""Action execution, recovery plan retrieval, and audit trail endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import Analysis, RecoveryAction
from app.services.audit_service import get_audit_trail
from app.services.execution_service import execute_approved_action

router = APIRouter(tags=["Recovery & Audit"])


class ExecuteApprovedRequest(BaseModel):
    """Request payload to execute an explicitly approved action with its one-time token."""

    action_id: str
    approval_token: str


@router.post(
    "/api/actions/execute-approved",
    summary="Execute an approved recovery action using its one-time token",
)
async def execute_approved(
    body: ExecuteApprovedRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Verify token, revalidate deterministically, and execute approved action."""
    try:
        return execute_approved_action(
            db,
            action_record_id=body.action_id,
            approval_token=body.approval_token,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get(
    "/api/recovery/{analysis_id}",
    summary="Get validated recovery actions and approval status for an analysis",
)
async def get_recovery_actions(
    analysis_id: str,
    db: Session = Depends(get_db),
) -> dict:
    """Return all recovery actions with validation, approval, and execution statuses."""
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis '{analysis_id}' not found.",
        )
    actions = (
        db.query(RecoveryAction)
        .filter(RecoveryAction.analysis_id == analysis_id)
        .order_by(RecoveryAction.created_at.asc())
        .all()
    )
    return {
        "analysis_id": analysis_id,
        "simulation_mode": analysis.simulation_mode,
        "actions": [
            {
                "id": a.id,
                "action_id": a.action_id,
                "action_type": a.action_type,
                "event_id": a.event_id,
                "description": a.description,
                "reason": a.reason,
                "parameters": a.parameters,
                "data_source": a.data_source,
                "validation_status": a.validation_status,
                "validation_reason": a.validation_reason,
                "approval_status": a.approval_status,
                "execution_status": a.execution_status,
                "execution_result": a.execution_result,
                "created_at": a.created_at.isoformat(),
            }
            for a in actions
        ],
    }


@router.get(
    "/api/audit/{analysis_id}",
    summary="Get chronological audit log for an analysis",
)
async def get_audit_logs(
    analysis_id: str,
    db: Session = Depends(get_db),
) -> dict:
    """Return all recorded agent, validator, approval, and execution audit events."""
    logs = get_audit_trail(db, analysis_id)
    return {
        "analysis_id": analysis_id,
        "count": len(logs),
        "audit_logs": [
            {
                "id": log.id,
                "actor": log.actor,
                "event_type": log.event_type,
                "simulation_mode": log.simulation_mode,
                "details": log.details,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ],
    }
