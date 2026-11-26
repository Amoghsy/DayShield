"""Service that persists ADK workflow runs, deterministic validation, and audit logs."""

from __future__ import annotations

import uuid
from typing import Any
from sqlalchemy.orm import Session

from app.agents.workflow import run_analysis_workflow
from app.api.schemas.analysis import AnalysisResultResponse, AnalysisStartRequest
from app.database.models import AgentExecutionLog, Analysis, CalendarEventCache, RecoveryAction
from app.services.audit_service import record_audit
from app.services.validation_service import validate_action


async def execute_and_persist_analysis(
    db: Session,
    request: AnalysisStartRequest,
    *,
    analysis_id: str | None = None,
    workflow_runner: Any = None,
) -> AnalysisResultResponse:
    """Run the 4-agent ADK workflow, validate recovery actions, and persist to SQLite."""
    aid = analysis_id or str(uuid.uuid4())
    runner_fn = workflow_runner or run_analysis_workflow

    agent_events: list[dict] = []

    def _on_event(ev: dict) -> None:
        agent_events.append(ev)

    result: AnalysisResultResponse = await runner_fn(
        request,
        analysis_id=aid,
        event_callback=_on_event,
    )

    db_analysis = Analysis(
        id=aid,
        status=result.status,
        simulation_mode=result.simulation_mode,
        request_payload=request.model_dump(),
        commute_assessment=result.commute_assessment.model_dump() if result.commute_assessment else None,
        schedule_assessment=result.schedule_assessment.model_dump() if result.schedule_assessment else None,
        priority_assessment=result.priority_assessment.model_dump() if result.priority_assessment else None,
        recovery_plan=result.recovery_plan.model_dump() if result.recovery_plan else None,
        error=result.error,
    )
    db.add(db_analysis)
    db.flush()

    # Persist calendar event cache
    if result.schedule_assessment:
        for ev in result.schedule_assessment.impacted_events:
            db.add(
                CalendarEventCache(
                    analysis_id=aid,
                    event_id=ev.event_id,
                    title=ev.title,
                    start_time=ev.start_time,
                    end_time=ev.end_time,
                    data_source=result.schedule_assessment.data_source,
                    raw_payload=ev.model_dump(),
                )
            )

    # Persist agent execution logs
    for ev in agent_events:
        author = ev.get("author") or "workflow"
        db.add(
            AgentExecutionLog(
                analysis_id=aid,
                agent_name=str(author),
                status="completed",
                message=f"Agent/node '{author}' emitted event.",
            )
        )

    # Deterministically validate and persist every proposed recovery action
    if result.recovery_plan:
        data_source = (
            result.commute_assessment.data_source
            if result.commute_assessment
            else ("simulated" if result.simulation_mode else "estimated")
        )
        for proposed in result.recovery_plan.recovery_plan:
            outcome = validate_action(
                proposed,
                result.commute_assessment,
                result.schedule_assessment,
                result.priority_assessment,
            )
            action_record_id = f"{aid}:{proposed.action_id}"
            db.add(
                RecoveryAction(
                    id=action_record_id,
                    analysis_id=aid,
                    action_id=proposed.action_id,
                    action_type=proposed.action_type,
                    event_id=proposed.event_id,
                    description=proposed.description,
                    reason=proposed.reason,
                    parameters=proposed.parameters,
                    data_source=data_source,
                    validation_status="valid" if outcome.valid else "rejected",
                    validation_reason=outcome.reason,
                    approval_status="pending",
                    execution_status="not_executed",
                )
            )
            record_audit(
                db,
                analysis_id=aid,
                actor="deterministic_validator",
                event_type="action_validated" if outcome.valid else "action_validation_rejected",
                simulation_mode=result.simulation_mode,
                details={
                    "action_record_id": action_record_id,
                    "action_type": proposed.action_type,
                    "valid": outcome.valid,
                    "reason": outcome.reason,
                },
            )

    db.commit()
    return result
