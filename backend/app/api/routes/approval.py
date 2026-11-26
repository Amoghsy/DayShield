"""Approval gate endpoints (explicit user approve/reject)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.services.approval_service import approve_action, reject_action

router = APIRouter(prefix="/api/approval", tags=["Approval Gate"])


class RejectRequest(BaseModel):
    """Optional reason when rejecting a proposed action."""

    reason: str = ""


@router.post("/{action_id}/approve", summary="Approve a validated recovery action")
async def approve_recovery_action(
    action_id: str,
    db: Session = Depends(get_db),
) -> dict:
    """Issue a one-time HMAC-bound approval token for a validated action."""
    try:
        return approve_action(db, action_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post("/{action_id}/reject", summary="Reject a proposed recovery action")
async def reject_recovery_action(
    action_id: str,
    body: RejectRequest | None = None,
    db: Session = Depends(get_db),
) -> dict:
    """Reject a proposed recovery action so it can never be executed."""
    try:
        return reject_action(db, action_id, reason=body.reason if body else "")
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
