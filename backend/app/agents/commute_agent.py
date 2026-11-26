"""Agent 1: Commute Agent using Google ADK."""

from __future__ import annotations

from google.adk import Agent
from google.adk.models.base_llm import BaseLlm

from app.agents.prompts import COMMUTE_AGENT_INSTRUCTION
from app.api.schemas.analysis import CommuteAssessment
from app.config import get_settings


def get_commute_route_and_weather(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    simulation_enabled: bool = True,
    added_delay_minutes: int = 25,
    weather_condition: str = "Moderate rain",
) -> dict:
    """Retrieve route duration and weather context (Phase 1 mock/simulation provider).

    In Phase 2, this tool delegates to the OSRM & Open-Meteo MCP tools when
    simulation_enabled is False.
    """
    baseline_minutes = 25
    if simulation_enabled:
        estimated_minutes = baseline_minutes + max(0, added_delay_minutes)
        data_source = "simulated"
        route_name = "route_outer_ring_alt_sim"
        alternatives = ["route_outer_ring_alt_sim", "route_bellary_rd_sim"]
        weather_text = f"{weather_condition} (simulated)"
    else:
        estimated_minutes = 28
        data_source = "estimated"
        route_name = "route_osrm_primary_mock"
        alternatives = ["route_osrm_primary_mock", "route_osrm_secondary_mock"]
        weather_text = "Partly cloudy, 24°C (sample)"

    delay_minutes = max(0, estimated_minutes - baseline_minutes)
    return {
        "baseline_travel_minutes": baseline_minutes,
        "estimated_travel_minutes": estimated_minutes,
        "delay_minutes": delay_minutes,
        "recommended_route": route_name,
        "alternative_routes": alternatives,
        "weather_context": weather_text,
        "data_source": data_source,
        "origin": {"lat": origin_lat, "lon": origin_lon},
        "destination": {"lat": dest_lat, "lon": dest_lon},
    }


def create_commute_agent(model: str | BaseLlm | None = None) -> Agent:
    """Create the Commute Agent (ADK Agent with structured CommuteAssessment output)."""
    settings = get_settings()
    return Agent(
        name="commute_agent",
        model=model or settings.gemini_model,
        description="Analyzes commute route duration, weather context, and delay risk.",
        instruction=COMMUTE_AGENT_INSTRUCTION,
        tools=[get_commute_route_and_weather],
        output_schema=CommuteAssessment,
        output_key="commute_assessment",
        disallow_transfer_to_parent=True,
        disallow_transfer_to_peers=True,
    )
