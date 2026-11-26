"""Deterministic priority scoring service for calendar commitments.

The Priority Agent uses this service so that priority scores (0-100) are
transparent, configurable, and never arbitrarily altered by an LLM.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.api.schemas.analysis import ImpactedEvent

# Default configurable base scores by commitment category (0-100 scale)
DEFAULT_CATEGORY_SCORES: dict[str, int] = {
    "examination": 100,
    "interview": 95,
    "client_meeting": 90,
    "internal_meeting": 65,
    "personal_task": 35,
    "other": 50,
}


@dataclass(frozen=True)
class PriorityScoringConfig:
    """Configurable weights for deterministic priority scoring."""

    external_attendee_bonus: int = 10
    in_person_only_bonus: int = 5
    high_lateness_threshold_minutes: int = 15
    high_lateness_bonus: int = 5
    online_join_discount: int = 5


def score_event(
    event: ImpactedEvent,
    config: PriorityScoringConfig | None = None,
) -> dict:
    """Compute a deterministic priority score (0-100) and recommended handling.

    Args:
        event: The impacted calendar event to score.
        config: Optional scoring weight overrides.

    Returns:
        Dictionary with event_id, title, priority_score, priority tier,
        recommended_handling, and deterministic_factors.
    """
    cfg = config or PriorityScoringConfig()
    base = DEFAULT_CATEGORY_SCORES.get(event.event_category, 50)
    score = base
    factors: list[str] = [f"base({event.event_category})={base}"]

    if event.has_external_attendees:
        score += cfg.external_attendee_bonus
        factors.append(f"external_attendees=+{cfg.external_attendee_bonus}")

    if not event.can_join_online and not event.is_online:
        score += cfg.in_person_only_bonus
        factors.append(f"in_person_required=+{cfg.in_person_only_bonus}")
    elif event.can_join_online and not event.is_online:
        score -= cfg.online_join_discount
        factors.append(f"online_fallback=-{cfg.online_join_discount}")

    if event.minutes_late >= cfg.high_lateness_threshold_minutes:
        score += cfg.high_lateness_bonus
        factors.append(f"lateness>={cfg.high_lateness_threshold_minutes}m=+{cfg.high_lateness_bonus}")

    # Clamp to [0, 100]
    score = max(0, min(100, score))

    priority: Literal["critical", "high", "medium", "low"]
    if score >= 85:
        priority = "critical"
    elif score >= 65:
        priority = "high"
    elif score >= 45:
        priority = "medium"
    else:
        priority = "low"

    # Determine recommended handling
    if event.minutes_late == 0:
        handling: Literal["protect", "join_online", "reschedule", "monitor"] = "monitor"
    elif priority == "critical":
        handling = "join_online" if event.can_join_online else "protect"
    elif priority == "high":
        handling = "join_online" if event.can_join_online else "protect"
    elif priority == "medium":
        handling = "join_online" if event.can_join_online else "reschedule"
    else:
        handling = "reschedule"

    return {
        "event_id": event.event_id,
        "title": event.title,
        "priority_score": score,
        "priority": priority,
        "recommended_handling": handling,
        "deterministic_factors": ", ".join(factors),
    }


def score_events(
    events: list[ImpactedEvent],
    config: PriorityScoringConfig | None = None,
) -> list[dict]:
    """Score and sort impacted events from highest to lowest priority_score."""
    scored = [score_event(ev, config=config) for ev in events]
    scored.sort(key=lambda item: item["priority_score"], reverse=True)
    return scored
