"""Agent 2: Schedule Agent using Google ADK."""

from __future__ import annotations

from google.adk import Agent
from google.adk.models.base_llm import BaseLlm

from app.agents.prompts import SCHEDULE_AGENT_INSTRUCTION
from app.api.schemas.analysis import ScheduleAssessment
from app.config import get_settings


def get_today_schedule_context(
    estimated_delay_minutes: int = 25,
    scenario: str = "scenario_a",
) -> dict:
    """Retrieve today's calendar events and free slots (Phase 1 sample provider).

    In Phase 3, this tool delegates to the Google Calendar MCP tool when OAuth
    is connected, falling back to clearly labeled sample data when unavailable.
    """
    if scenario == "scenario_b":
        events = [
            {
                "event_id": "sample_evt_201",
                "title": "Internal Sprint Sync",
                "start_time": "09:00",
                "end_time": "09:45",
                "location": "Room 302 / Google Meet",
                "attendees": ["teammate1@example.com", "teammate2@example.com"],
                "has_external_attendees": False,
                "is_online": False,
                "can_join_online": True,
                "minutes_late": estimated_delay_minutes,
                "impact_level": "medium" if estimated_delay_minutes > 0 else "none",
                "event_category": "internal_meeting",
            },
            {
                "event_id": "sample_evt_202",
                "title": "Gym & Errands",
                "start_time": "17:00",
                "end_time": "18:00",
                "location": "Local Gym",
                "attendees": [],
                "has_external_attendees": False,
                "is_online": False,
                "can_join_online": False,
                "minutes_late": 0,
                "impact_level": "none",
                "event_category": "personal_task",
            },
        ]
    else:
        events = [
            {
                "event_id": "sample_evt_101",
                "title": "Client Project Review",
                "start_time": "09:00",
                "end_time": "10:00",
                "location": "MSRIT Innovation Lab",
                "attendees": ["client.lead@acmecorp.com", "mentor@msrit.edu"],
                "has_external_attendees": True,
                "is_online": False,
                "can_join_online": True,
                "minutes_late": estimated_delay_minutes,
                "impact_level": "high" if estimated_delay_minutes >= 15 else "medium",
                "event_category": "client_meeting",
            },
            {
                "event_id": "sample_evt_102",
                "title": "Internal Standup",
                "start_time": "10:30",
                "end_time": "11:00",
                "location": "Online",
                "attendees": ["team@dayshield.local"],
                "has_external_attendees": False,
                "is_online": True,
                "can_join_online": True,
                "minutes_late": 0,
                "impact_level": "none",
                "event_category": "internal_meeting",
            },
        ]

    free_slots = [
        {"start_time": "11:00", "end_time": "12:30", "duration_minutes": 90},
        {"start_time": "14:00", "end_time": "15:30", "duration_minutes": 90},
    ]

    return {
        "data_source": "sample",
        "events": events,
        "free_slots": free_slots,
    }


def create_schedule_agent(model: str | BaseLlm | None = None) -> Agent:
    """Create the Schedule Agent (ADK Agent with structured ScheduleAssessment output)."""
    settings = get_settings()
    return Agent(
        name="schedule_agent",
        model=model or settings.gemini_model,
        description="Inspects today's calendar commitments, lateness, and free slots.",
        instruction=SCHEDULE_AGENT_INSTRUCTION,
        tools=[get_today_schedule_context],
        output_schema=ScheduleAssessment,
        output_key="schedule_assessment",
        disallow_transfer_to_parent=True,
        disallow_transfer_to_peers=True,
    )
