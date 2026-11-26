"""Structured Pydantic schemas for DayShield multi-agent analysis and API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field


DataSourceType = Literal["live", "estimated", "simulated", "sample"]


class Coordinates(BaseModel):
    """Geographic coordinates (latitude, longitude)."""

    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    label: str = Field(default="", description="Optional human-readable location name")


class SimulationConfig(BaseModel):
    """Optional simulation parameters for deterministic hackathon demos."""

    enabled: bool = False
    scenario: Literal["scenario_a", "scenario_b", "scenario_c", "custom"] = "scenario_a"
    added_delay_minutes: int = Field(default=25, ge=0, le=240)
    weather_condition: str = Field(default="Moderate rain")


class AnalysisStartRequest(BaseModel):
    """Request payload to start a DayShield commute disruption analysis."""

    origin: Coordinates = Field(
        default_factory=lambda: Coordinates(
            latitude=12.9716, longitude=77.5946, label="Home (Bengaluru)"
        )
    )
    destination: Coordinates = Field(
        default_factory=lambda: Coordinates(
            latitude=13.0306, longitude=77.5649, label="MSRIT Campus"
        )
    )
    required_arrival_time: str = Field(
        default="09:00",
        description="Target arrival time in HH:MM (24-hour) user local time.",
    )
    departure_time: str = Field(
        default="08:25",
        description="Planned departure time in HH:MM (24-hour) user local time.",
    )
    simulation: SimulationConfig = Field(default_factory=SimulationConfig)


# ---------------------------------------------------------------------------
# Agent 1: Commute Agent Output Schema
# ---------------------------------------------------------------------------
class CommuteAssessment(BaseModel):
    """Structured output from the Commute Agent."""

    agent: Literal["commute_agent"] = "commute_agent"
    status: Literal["on_time", "at_risk", "disrupted"]
    estimated_travel_minutes: int = Field(..., ge=0)
    baseline_travel_minutes: int = Field(..., ge=0)
    delay_minutes: int = Field(..., ge=0)
    recommended_route: str
    alternative_routes: list[str] = Field(default_factory=list)
    weather_context: str
    data_source: DataSourceType
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning_summary: str


# ---------------------------------------------------------------------------
# Agent 2: Schedule Agent Output Schema
# ---------------------------------------------------------------------------
class ImpactedEvent(BaseModel):
    """A calendar event potentially affected by the commute disruption."""

    event_id: str
    title: str
    start_time: str
    end_time: str
    location: str = ""
    attendees: list[str] = Field(default_factory=list)
    has_external_attendees: bool = False
    is_online: bool = False
    can_join_online: bool = False
    minutes_late: int = Field(default=0, ge=0)
    impact_level: Literal["none", "low", "medium", "high", "critical"] = "none"
    event_category: Literal[
        "examination",
        "interview",
        "client_meeting",
        "internal_meeting",
        "personal_task",
        "other",
    ] = "other"


class FreeSlot(BaseModel):
    """An available time window on the user's calendar."""

    start_time: str
    end_time: str
    duration_minutes: int = Field(..., ge=0)


class ScheduleAssessment(BaseModel):
    """Structured output from the Schedule Agent."""

    agent: Literal["schedule_agent"] = "schedule_agent"
    impacted_events: list[ImpactedEvent] = Field(default_factory=list)
    free_slots: list[FreeSlot] = Field(default_factory=list)
    data_source: DataSourceType = "sample"
    schedule_summary: str


# ---------------------------------------------------------------------------
# Impact Merge State (Deterministic Merge of Agent 1 + Agent 2)
# ---------------------------------------------------------------------------
class ImpactMergeResult(BaseModel):
    """Deterministic merge of CommuteAssessment and ScheduleAssessment."""

    commute: CommuteAssessment
    schedule: ScheduleAssessment
    disruption_detected: bool
    effective_delay_minutes: int
    impacted_count: int
    data_sources: dict[str, DataSourceType]


# ---------------------------------------------------------------------------
# Agent 3: Priority Agent Output Schema
# ---------------------------------------------------------------------------
class RankedEvent(BaseModel):
    """Priority evaluation for an impacted calendar event."""

    event_id: str
    title: str = ""
    priority_score: int = Field(..., ge=0, le=100)
    priority: Literal["critical", "high", "medium", "low"]
    recommended_handling: Literal["protect", "join_online", "reschedule", "monitor"]
    reason: str


class PriorityAssessment(BaseModel):
    """Structured output from the Priority Agent."""

    agent: Literal["priority_agent"] = "priority_agent"
    ranked_events: list[RankedEvent] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Agent 4: Recovery Agent Output Schema
# ---------------------------------------------------------------------------
ActionType = Literal[
    "create_email_draft",
    "suggest_online_join",
    "reschedule_event",
    "switch_route",
    "notify_only",
]


class ProposedRecoveryAction(BaseModel):
    """A single proposed recovery action (never auto-executed)."""

    action_id: str
    action_type: ActionType
    event_id: str | None = None
    description: str
    reason: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    requires_approval: bool = True


class RecoveryPlan(BaseModel):
    """Structured output from the Recovery Agent."""

    agent: Literal["recovery_agent"] = "recovery_agent"
    recovery_plan: list[ProposedRecoveryAction] = Field(default_factory=list)
    summary: str = ""


# ---------------------------------------------------------------------------
# Full Workflow Output & API Responses
# ---------------------------------------------------------------------------
class AnalysisResultResponse(BaseModel):
    """Complete multi-agent analysis result returned by DayShield."""

    analysis_id: str
    status: Literal["running", "completed", "failed"]
    simulation_mode: bool
    created_at: datetime
    commute_assessment: CommuteAssessment | None = None
    schedule_assessment: ScheduleAssessment | None = None
    priority_assessment: PriorityAssessment | None = None
    recovery_plan: RecoveryPlan | None = None
    error: str | None = None
