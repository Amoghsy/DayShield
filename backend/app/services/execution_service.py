"""Approval-controlled action executor.

Never executes an action without:
1. Validating the one-time HMAC approval token (signature, expiry, parameter hash, unused).
2. Revalidating the action deterministically immediately before execution.
3. Preventing duplicate execution.
"""

from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.api.schemas.analysis import (
    CommuteAssessment,
    PriorityAssessment,
    ProposedRecoveryAction,
    ScheduleAssessment,
)
from app.database.models import Analysis, ApprovalRecord, RecoveryAction
from app.integrations.gmail_client import GmailDraftClient
from app.integrations.google_calendar import GoogleCalendarClient
from app.services.audit_service import record_audit
from app.services.validation_service import validate_action
from app.utils.security import hash_token, verify_approval_token


def execute_approved_action(
    db: Session,
    *,
    action_record_id: str,
    approval_token: str,
) -> dict:
    """Verify approval token, revalidate deterministically, and execute the approved action."""
    action = db.query(RecoveryAction).filter(RecoveryAction.id == action_record_id).first()
    if action is None:
        raise ValueError(f"Recovery action '{action_record_id}' not found.")

    if action.approval_status != "approved":
        raise PermissionError(
            f"Action '{action_record_id}' is not approved (status={action.approval_status})."
        )

    if action.execution_status == "executed":
        raise PermissionError(f"Action '{action_record_id}' was already executed.")

    # Verify cryptographic token binding & expiry
    ok, msg = verify_approval_token(
        raw_token=approval_token,
        expected_action_record_id=action.id,
        expected_parameters=action.parameters or {},
    )
    if not ok:
        raise PermissionError(msg)

    # Verify token exists in DB and has not been consumed
    tok_hash = hash_token(approval_token)
    approval_rec = (
        db.query(ApprovalRecord)
        .filter(
            ApprovalRecord.action_record_id == action.id,
            ApprovalRecord.token_hash == tok_hash,
            ApprovalRecord.decision == "approved",
        )
        .first()
    )
    if approval_rec is None:
        raise PermissionError("Approval token record not found.")
    if approval_rec.consumed:
        raise PermissionError("Approval token has already been used.")

    # Revalidate deterministically immediately before execution
    analysis = db.query(Analysis).filter(Analysis.id == action.analysis_id).first()
    sim_mode = analysis.simulation_mode if analysis else True
    commute = (
        CommuteAssessment.model_validate(analysis.commute_assessment)
        if analysis and analysis.commute_assessment
        else None
    )
    schedule = (
        ScheduleAssessment.model_validate(analysis.schedule_assessment)
        if analysis and analysis.schedule_assessment
        else None
    )
    priority = (
        PriorityAssessment.model_validate(analysis.priority_assessment)
        if analysis and analysis.priority_assessment
        else None
    )

    proposed = ProposedRecoveryAction(
        action_id=action.action_id,
        action_type=action.action_type,  # type: ignore[arg-type]
        event_id=action.event_id,
        description=action.description,
        reason=action.reason,
        parameters=action.parameters or {},
        requires_approval=True,
    )
    revalidation = validate_action(proposed, commute, schedule, priority)
    if not revalidation.valid:
        raise PermissionError(f"Pre-execution revalidation failed: {revalidation.reason}")

    # Consume token BEFORE external call to prevent race/duplicate execution
    approval_rec.consumed = True
    approval_rec.consumed_at = datetime.now(timezone.utc)

    params = action.parameters or {}
    if action.action_type == "create_email_draft":
        result = GmailDraftClient().create_draft(
            recipient=str(params.get("recipient", "")),
            subject=str(params.get("subject", "Commute Delay Notice")),
            body=str(params.get("body", action.description)),
        )
    elif action.action_type == "reschedule_event":
        result = GoogleCalendarClient().reschedule_event(
            event_id=str(action.event_id or ""),
            new_start_iso=str(params.get("new_start_time", "")),
            new_end_iso=str(params.get("new_end_time", "")),
        )
    else:
        result = {
            "ok": True,
            "mode": "advisory",
            "action_type": action.action_type,
            "message": f"Confirmed non-destructive action: {action.description}",
        }

    action.execution_status = "executed"
    action.execution_result = result
    db.commit()

    record_audit(
        db,
        analysis_id=action.analysis_id,
        actor="executor",
        event_type="action_executed",
        simulation_mode=sim_mode,
        details={
            "action_record_id": action.id,
            "action_type": action.action_type,
            "result": result,
        },
    )

    return {
        "action_id": action.id,
        "execution_status": "executed",
        "result": result,
    }
