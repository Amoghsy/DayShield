"""Google ADK graph-based Workflow orchestration for DayShield.

Workflow topology:
    START
      |---> commute_agent  ---|
      |---> schedule_agent ---|--> impact_join --> impact_merge --> priority_agent --> recovery_agent

Uses google.adk.Workflow (graph-based API in ADK 2.8+) instead of deprecated
SequentialAgent / ParallelAgent / LoopAgent patterns.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from google.adk import Runner, Workflow
from google.adk.agents.context import Context
from google.adk.models.base_llm import BaseLlm
from google.adk.sessions import InMemorySessionService
from google.adk.workflow import JoinNode, START, node
from google.genai import types
from pydantic import BaseModel

from app.agents.commute_agent import create_commute_agent
from app.agents.priority_agent import create_priority_agent
from app.agents.recovery_agent import create_recovery_agent
from app.agents.schedule_agent import create_schedule_agent
from app.api.schemas.analysis import (
    AnalysisResultResponse,
    AnalysisStartRequest,
    CommuteAssessment,
    ImpactMergeResult,
    PriorityAssessment,
    RecoveryPlan,
    ScheduleAssessment,
)

logger = logging.getLogger("dayshield.workflow")

APP_NAME = "dayshield"


class DayShieldWorkflowState(BaseModel):
    """Typed session state for the DayShield ADK Workflow."""

    commute_assessment: CommuteAssessment | dict[str, Any] | None = None
    schedule_assessment: ScheduleAssessment | dict[str, Any] | None = None
    impact_merge: ImpactMergeResult | dict[str, Any] | None = None
    priority_assessment: PriorityAssessment | dict[str, Any] | None = None
    recovery_plan: RecoveryPlan | dict[str, Any] | None = None


def _coerce_model(raw: Any, model_cls: type[BaseModel]) -> Any:
    """Safely parse a dict, JSON string, or BaseModel into `model_cls`."""
    if raw is None:
        return None
    if isinstance(raw, model_cls):
        return raw
    if isinstance(raw, str):
        raw = json.loads(raw)
    if isinstance(raw, dict):
        return model_cls.model_validate(raw)
    return model_cls.model_validate(raw, from_attributes=True)


@node(name="impact_merge")
async def merge_impact_assessments(ctx: Context) -> dict[str, Any]:
    """Deterministically merge CommuteAssessment and ScheduleAssessment in state."""
    state = ctx.state
    commute = _coerce_model(state.get("commute_assessment"), CommuteAssessment)
    schedule = _coerce_model(state.get("schedule_assessment"), ScheduleAssessment)

    if commute is None or schedule is None:
        raise ValueError(
            "Both commute_assessment and schedule_assessment must be present before merging."
        )

    # Propagate commute delay into impacted events if schedule didn't have exact delay yet
    updated_events = []
    for ev in schedule.impacted_events:
        if not ev.is_online and ev.minutes_late == 0 and commute.delay_minutes > 0:
            ev = ev.model_copy(update={"minutes_late": commute.delay_minutes})
        updated_events.append(ev)

    schedule = schedule.model_copy(update={"impacted_events": updated_events})
    state["schedule_assessment"] = schedule.model_dump()

    impacted_count = sum(1 for ev in schedule.impacted_events if ev.minutes_late > 0)
    merged = ImpactMergeResult(
        commute=commute,
        schedule=schedule,
        disruption_detected=commute.status != "on_time" or commute.delay_minutes > 0,
        effective_delay_minutes=commute.delay_minutes,
        impacted_count=impacted_count,
        data_sources={
            "commute": commute.data_source,
            "schedule": schedule.data_source,
        },
    )
    state["impact_merge"] = merged.model_dump()
    return {"impact_merge": merged.model_dump()}


def build_dayshield_workflow(model: str | BaseLlm | None = None) -> Workflow:
    """Construct the DayShield ADK graph Workflow with parallel + sequential stages."""
    commute_agent = create_commute_agent(model=model)
    schedule_agent = create_schedule_agent(model=model)
    priority_agent = create_priority_agent(model=model)
    recovery_agent = create_recovery_agent(model=model)
    impact_join = JoinNode(name="impact_join")

    return Workflow(
        name="dayshield_recovery_workflow",
        description=(
            "Concurrent commute & schedule analysis followed by deterministic merge, "
            "priority scoring, and approval-first recovery planning."
        ),
        state_schema=DayShieldWorkflowState,
        edges=[
            (START, (commute_agent, schedule_agent)),
            (commute_agent, impact_join),
            (schedule_agent, impact_join),
            (impact_join, merge_impact_assessments, priority_agent, recovery_agent),
        ],
    )


def _build_initial_prompt(request: AnalysisStartRequest) -> str:
    """Create the structured user prompt passed to the ADK Workflow."""
    payload = {
        "origin": request.origin.model_dump(),
        "destination": request.destination.model_dump(),
        "required_arrival_time": request.required_arrival_time,
        "departure_time": request.departure_time,
        "simulation": request.simulation.model_dump(),
    }
    return (
        "Analyze the user's commute and today's schedule for disruption, "
        "prioritize impacted commitments, and propose an approval-first recovery plan.\n"
        f"Input Context:\n{json.dumps(payload, indent=2)}"
    )


async def run_analysis_workflow(
    request: AnalysisStartRequest,
    *,
    analysis_id: str | None = None,
    user_id: str = "demo_user",
    model: str | BaseLlm | None = None,
    event_callback: Any = None,
) -> AnalysisResultResponse:
    """Execute the DayShield ADK Workflow and return typed Pydantic results.

    Args:
        request: AnalysisStartRequest with origin, destination, times, and simulation config.
        analysis_id: Optional UUID string; generated if omitted.
        user_id: User identifier for the ADK session.
        model: Optional Gemini model name or custom BaseLlm (useful for testing).
        event_callback: Optional async or sync callable(event_dict) for live status updates.
    """
    aid = analysis_id or str(uuid.uuid4())
    created_at = datetime.now(timezone.utc)
    session_service = InMemorySessionService()
    workflow = build_dayshield_workflow(model=model)

    runner = Runner(
        app_name=APP_NAME,
        agent=workflow,
        session_service=session_service,
        auto_create_session=True,
    )

    user_message = types.Content(
        role="user",
        parts=[types.Part.from_text(text=_build_initial_prompt(request))],
    )

    try:
        async for event in runner.run_async(
            user_id=user_id,
            session_id=aid,
            new_message=user_message,
        ):
            if event_callback is not None:
                info = {
                    "author": getattr(event, "author", None),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                res = event_callback(info)
                if hasattr(res, "__await__"):
                    await res

        session = await session_service.get_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=aid,
        )
        state = session.state if session else {}

        commute = _coerce_model(state.get("commute_assessment"), CommuteAssessment)
        schedule = _coerce_model(state.get("schedule_assessment"), ScheduleAssessment)
        priority = _coerce_model(state.get("priority_assessment"), PriorityAssessment)
        recovery = _coerce_model(state.get("recovery_plan"), RecoveryPlan)

        return AnalysisResultResponse(
            analysis_id=aid,
            status="completed",
            simulation_mode=request.simulation.enabled,
            created_at=created_at,
            commute_assessment=commute,
            schedule_assessment=schedule,
            priority_assessment=priority,
            recovery_plan=recovery,
        )
    except Exception as exc:
        logger.exception("Workflow execution failed for analysis_id=%s", aid)
        return AnalysisResultResponse(
            analysis_id=aid,
            status="failed",
            simulation_mode=request.simulation.enabled,
            created_at=created_at,
            error=str(exc),
        )
