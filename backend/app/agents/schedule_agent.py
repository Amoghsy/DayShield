"""Agent 2: Schedule Agent using Google ADK."""

from __future__ import annotations

from google.adk import Agent
from google.adk.models.base_llm import BaseLlm

from app.agents.prompts import SCHEDULE_AGENT_INSTRUCTION
from app.api.schemas.analysis import ScheduleAssessment
from app.config import get_settings
from app.integrations.google_calendar import GoogleCalendarClient
from app.mcp_servers.client import create_dayshield_mcp_toolset


def get_today_schedule_context(
    estimated_delay_minutes: int = 25,
    scenario: str = "scenario_a",
) -> dict:
    """Retrieve today's calendar events and free slots.

    Uses Google Calendar API when OAuth is connected, falling back to clearly
    labeled sample data when unavailable.
    """
    raw = GoogleCalendarClient().get_today_events(scenario=scenario)
    events = []
    for ev in raw.get("events", []):
        ev_copy = dict(ev)
        is_online = bool(ev_copy.get("is_online", False))
        minutes_late = 0 if is_online or ev_copy.get("event_category") == "personal_task" else max(0, estimated_delay_minutes)
        if minutes_late == 0:
            impact = "none"
        elif minutes_late >= 15:
            impact = "high"
        else:
            impact = "medium"
        ev_copy["minutes_late"] = minutes_late
        ev_copy["impact_level"] = impact
        events.append(ev_copy)

    return {
        "data_source": raw.get("data_source", "sample"),
        "oauth_connected": raw.get("oauth_connected", False),
        "events": events,
        "free_slots": raw.get("free_slots", []),
    }


def create_schedule_agent(
    model: str | BaseLlm | None = None,
    use_mcp: bool = False,
) -> Agent:
    """Create the Schedule Agent (ADK Agent with structured ScheduleAssessment output)."""
    settings = get_settings()
    tools: list = [get_today_schedule_context]
    if use_mcp:
        tools.append(
            create_dayshield_mcp_toolset(
                tool_filter=[
                    "get_today_events",
                    "get_event_details",
                    "get_available_slots",
                ]
            )
        )
    return Agent(
        name="schedule_agent",
        model=model or settings.gemini_model,
        description="Inspects today's calendar commitments, lateness, and free slots.",
        instruction=SCHEDULE_AGENT_INSTRUCTION,
        tools=tools,
        output_schema=ScheduleAssessment,
        output_key="schedule_assessment",
        disallow_transfer_to_parent=True,
        disallow_transfer_to_peers=True,
    )
