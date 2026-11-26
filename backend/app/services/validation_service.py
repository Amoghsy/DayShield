"""Deterministic Python validator between Recovery Agent and Approval Gate.

AI models can never bypass this validator. Every proposed action is checked
against real/current schedule events, protected-event rules, working hours,
verified routes, and recipient validity.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.api.schemas.analysis import (
    CommuteAssessment,
    PriorityAssessment,
    ProposedRecoveryAction,
    ScheduleAssessment,
)
from app.config import get_settings

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
SUPPORTED_ACTIONS = {
    "create_email_draft",
    "suggest_online_join",
    "reschedule_event",
    "switch_route",
    "notify_only",
}


@dataclass
class ValidationOutcome:
    """Result of deterministic validation for a single proposed action."""

    action_id: str
    valid: bool
    reason: str
    fallback_recommendation: str | None = None


def _parse_hour(time_str: str) -> int | None:
    """Extract hour (0-23) from 'HH:MM' or ISO datetime string."""
    if not time_str:
        return None
    if "T" in time_str:
        time_part = time_str.split("T", 1)[1]
    else:
        time_part = time_str
    try:
        return int(time_part.split(":")[0])
    except (ValueError, IndexError):
        return None


def _times_overlap(start_a: str, end_a: str, start_b: str, end_b: str) -> bool:
    """Check simple HH:MM overlap between two windows."""
    if len(start_a) < 5 or len(end_a) < 5 or len(start_b) < 5 or len(end_b) < 5:
        return False
    sa, ea = start_a[-5:], end_a[-5:]
    sb, eb = start_b[-5:], end_b[-5:]
    return sa < eb and sb < ea


def validate_action(
    action: ProposedRecoveryAction,
    commute: CommuteAssessment | None,
    schedule: ScheduleAssessment | None,
    priority: PriorityAssessment | None,
) -> ValidationOutcome:
    """Validate a single ProposedRecoveryAction using deterministic Python rules."""
    if action.action_type not in SUPPORTED_ACTIONS:
        return ValidationOutcome(
            action_id=action.action_id,
            valid=False,
            reason=f"Unsupported action_type '{action.action_type}'.",
            fallback_recommendation="Use 'notify_only' or 'create_email_draft'.",
        )

    events_by_id = {
        ev.event_id: ev for ev in (schedule.impacted_events if schedule else [])
    }
    ranked_by_id = {
        r.event_id: r for r in (priority.ranked_events if priority else [])
    }

    # Check event existence for event-bound actions
    if action.action_type in {"suggest_online_join", "reschedule_event"}:
        if not action.event_id or action.event_id not in events_by_id:
            return ValidationOutcome(
                action_id=action.action_id,
                valid=False,
                reason=f"Event ID '{action.event_id}' does not exist in today's schedule.",
                fallback_recommendation="Verify calendar events before proposing schedule changes.",
            )

    if action.action_type == "create_email_draft":
        recipient = str(action.parameters.get("recipient", "")).strip()
        if not EMAIL_REGEX.match(recipient):
            return ValidationOutcome(
                action_id=action.action_id,
                valid=False,
                reason=f"Invalid or missing email recipient '{recipient}'.",
                fallback_recommendation="Notify attendee manually or provide a valid email address.",
            )

    if action.action_type == "switch_route":
        route_id = str(action.parameters.get("route_id", "")).strip()
        verified_routes = set(commute.alternative_routes if commute else [])
        if commute and commute.recommended_route:
            verified_routes.add(commute.recommended_route)
        if not route_id or route_id not in verified_routes:
            return ValidationOutcome(
                action_id=action.action_id,
                valid=False,
                reason=f"Route ID '{route_id}' is not verified in the current commute analysis.",
                fallback_recommendation="Use the recommended route from Commute Assessment.",
            )

    if action.action_type == "reschedule_event":
        ranked = ranked_by_id.get(action.event_id or "")
        if ranked and (ranked.priority == "critical" or ranked.recommended_handling == "protect"):
            return ValidationOutcome(
                action_id=action.action_id,
                valid=False,
                reason=(
                    f"Event '{action.event_id}' is protected (priority={ranked.priority}, "
                    f"handling={ranked.recommended_handling}) and cannot be rescheduled."
                ),
                fallback_recommendation="Send a delay notice draft or join online instead.",
            )

        new_start = str(action.parameters.get("new_start_time", ""))
        new_end = str(action.parameters.get("new_end_time", ""))
        settings = get_settings()
        start_hr = _parse_hour(new_start)
        end_hr = _parse_hour(new_end)
        if start_hr is None or end_hr is None:
            return ValidationOutcome(
                action_id=action.action_id,
                valid=False,
                reason="Reschedule action requires valid 'new_start_time' and 'new_end_time'.",
                fallback_recommendation="Select an available slot within working hours.",
            )
        if start_hr < settings.work_hours_start or end_hr > settings.work_hours_end:
            return ValidationOutcome(
                action_id=action.action_id,
                valid=False,
                reason=(
                    f"Proposed time {new_start}-{new_end} is outside allowed working hours "
                    f"({settings.work_hours_start:02d}:00-{settings.work_hours_end:02d}:00)."
                ),
                fallback_recommendation="Pick a slot inside working hours.",
            )

        for other_id, other_ev in events_by_id.items():
            if other_id != action.event_id and _times_overlap(
                new_start, new_end, other_ev.start_time, other_ev.end_time
            ):
                return ValidationOutcome(
                    action_id=action.action_id,
                    valid=False,
                    reason=f"Proposed time conflicts with existing event '{other_ev.title}' ({other_ev.start_time}-{other_ev.end_time}).",
                    fallback_recommendation="Choose a non-overlapping free slot.",
                )

    return ValidationOutcome(
        action_id=action.action_id,
        valid=True,
        reason="Passed all deterministic safety and consistency checks.",
    )
