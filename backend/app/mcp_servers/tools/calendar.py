"""Read-only Calendar MCP tools (OAuth in Phase 3, sample fallback when disconnected)."""

from __future__ import annotations

from typing import Any

from app.agents.schedule_agent import get_today_schedule_context


def get_today_events(scenario: str = "scenario_a") -> dict[str, Any]:
    """Retrieve today's calendar events (sample data until Google OAuth is connected)."""
    ctx = get_today_schedule_context(estimated_delay_minutes=0, scenario=scenario)
    return {
        "data_source": ctx["data_source"],
        "events": ctx["events"],
    }


def get_event_details(event_id: str, scenario: str = "scenario_a") -> dict[str, Any]:
    """Retrieve details for a specific calendar event by ID."""
    ctx = get_today_schedule_context(estimated_delay_minutes=0, scenario=scenario)
    for ev in ctx["events"]:
        if ev["event_id"] == event_id:
            return {"found": True, "data_source": ctx["data_source"], "event": ev}
    return {"found": False, "data_source": ctx["data_source"], "error": f"Event '{event_id}' not found."}


def get_available_slots(start_time: str = "09:00", end_time: str = "18:00") -> dict[str, Any]:
    """Retrieve available free time slots between start_time and end_time (HH:MM)."""
    ctx = get_today_schedule_context(estimated_delay_minutes=0)
    slots = [
        slot
        for slot in ctx["free_slots"]
        if slot["start_time"] >= start_time and slot["end_time"] <= end_time
    ]
    return {"data_source": ctx["data_source"], "free_slots": slots}
