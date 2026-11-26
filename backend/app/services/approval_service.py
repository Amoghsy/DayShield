"""Approval gate service: issues and validates one-time parameter-bound tokens."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.database.models import Analysis, ApprovalRecord, RecoveryAction
from app.services.audit_service import record_audit
from app.utils.security import generate_approval_token, hash_parameters


def approve_action(db: Session, action_record_id: str) -> dict:
    """Explicitly approve a validated recovery action and issue a one-time token."""
    action = db.query(RecoveryAction).filter(RecoveryAction.id == action_record_id).first()
    if action is None:
        raise ValueError(f"Recovery action '{action_record_id}' not found.")

    if action.validation_status != "valid":
        raise ValueError(
            f"Cannot approve invalid action '{action_record_id}': {action.validation_reason}"
        )

    if action.execution_status == "executed":
        raise ValueError(f"Action '{action_record_id}' has already been executed.")

    analysis = db.query(Analysis).filter(Analysis.id == action.analysis_id).first()
    sim_mode = analysis.simulation_mode if analysis else True

    raw_token, tok_hash, params_hash, expires_at = generate_approval_token(
        action_record_id=action.id,
        parameters=action.parameters or {},
    )

    action.approval_status = "approved"
    record = ApprovalRecord(
        action_record_id=action.id,
        decision="approved",
        token_hash=tok_hash,
        parameters_hash=params_hash,
        expires_at=expires_at,
        consumed=False,
    )
    db.add(record)
    db.commit()

    record_audit(
        db,
        analysis_id=action.analysis_id,
        actor="user",
        event_type="action_approved",
        simulation_mode=sim_mode,
        details={
            "action_record_id": action.id,
            "action_type": action.action_type,
            "expires_at": expires_at.isoformat(),
        },
    )

    return {
        "action_id": action.id,
        "approval_status": "approved",
        "approval_token": raw_token,
        "expires_at": expires_at.isoformat(),
    }


def reject_action(db: Session, action_record_id: str, reason: str = "") -> dict:
    """Explicitly reject a proposed recovery action."""
    action = db.query(RecoveryAction).filter(RecoveryAction.id == action_record_id).first()
    if action is None:
        raise ValueError(f"Recovery action '{action_record_id}' not found.")

    analysis = db.query(Analysis).filter(Analysis.id == action.analysis_id).first()
    sim_mode = analysis.simulation_mode if analysis else True

    action.approval_status = "rejected"
    record = ApprovalRecord(
        action_record_id=action.id,
        decision="rejected",
        token_hash=None,
        parameters_hash=hash_parameters(action.parameters or {}),
        consumed=True,
        reason=reason,
    )
    db.add(record)
    db.commit()

    record_audit(
        db,
        analysis_id=action.analysis_id,
        actor="user",
        event_type="action_rejected",
        simulation_mode=sim_mode,
        details={"action_record_id": action.id, "reason": reason},
    )

    return {
        "action_id": action.id,
        "approval_status": "rejected",
        "reason": reason,
    }
