"""Agent 1: Commute Agent using Google ADK + OSRM/Open-Meteo + optional McpToolset."""

from __future__ import annotations

from google.adk import Agent
from google.adk.models.base_llm import BaseLlm

from app.agents.prompts import COMMUTE_AGENT_INSTRUCTION
from app.api.schemas.analysis import CommuteAssessment
from app.config import get_settings
from app.integrations.osrm_client import OSRMClient
from app.integrations.weather_client import WeatherClient
from app.mcp_servers.client import create_dayshield_mcp_toolset

_osrm = OSRMClient()
_weather = WeatherClient()


async def get_commute_route_and_weather(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    simulation_enabled: bool = True,
    added_delay_minutes: int = 25,
    weather_condition: str = "Moderate rain",
) -> dict:
    """Retrieve route duration and weather context.

    - In SIMULATION MODE: returns deterministic simulated delay & weather context.
    - In LIVE MODE: queries OSRM (route-estimate data, NOT live traffic) and Open-Meteo.
    """
    baseline_minutes = 25
    if simulation_enabled:
        estimated_minutes = baseline_minutes + max(0, added_delay_minutes)
        return {
            "baseline_travel_minutes": baseline_minutes,
            "estimated_travel_minutes": estimated_minutes,
            "delay_minutes": max(0, estimated_minutes - baseline_minutes),
            "recommended_route": "route_outer_ring_alt_sim",
            "alternative_routes": ["route_outer_ring_alt_sim", "route_bellary_rd_sim"],
            "weather_context": f"{weather_condition} (simulated)",
            "data_source": "simulated",
            "origin": {"lat": origin_lat, "lon": origin_lon},
            "destination": {"lat": dest_lat, "lon": dest_lon},
        }

    osrm_res = await _osrm.get_routes(origin_lat, origin_lon, dest_lat, dest_lon, alternatives=True)
    weather_res = await _weather.get_current_weather(origin_lat, origin_lon)

    if osrm_res.get("ok") and osrm_res.get("primary_route"):
        primary = osrm_res["primary_route"]
        estimated_minutes = primary["duration_minutes"]
        recommended_route = primary["route_id"]
        alternatives = [r["route_id"] for r in osrm_res.get("routes", [])]
        data_source = "estimated"
    else:
        estimated_minutes = baseline_minutes
        recommended_route = "fallback_unavailable"
        alternatives = []
        data_source = "estimated"

    return {
        "baseline_travel_minutes": baseline_minutes,
        "estimated_travel_minutes": estimated_minutes,
        "delay_minutes": max(0, estimated_minutes - baseline_minutes),
        "recommended_route": recommended_route,
        "alternative_routes": alternatives,
        "weather_context": weather_res.get("summary", "Weather unavailable"),
        "data_source": data_source,
        "osrm_disclaimer": osrm_res.get(
            "disclaimer",
            "OSRM provides route-estimate duration only, not live traffic congestion.",
        ),
        "origin": {"lat": origin_lat, "lon": origin_lon},
        "destination": {"lat": dest_lat, "lon": dest_lon},
    }


def create_commute_agent(
    model: str | BaseLlm | None = None,
    use_mcp: bool = False,
) -> Agent:
    """Create the Commute Agent (ADK Agent with structured CommuteAssessment output)."""
    settings = get_settings()
    tools: list = [get_commute_route_and_weather]
    if use_mcp:
        tools.append(
            create_dayshield_mcp_toolset(
                tool_filter=[
                    "get_route",
                    "get_alternative_routes",
                    "calculate_route_duration",
                    "get_current_weather",
                    "get_weather_forecast",
                ]
            )
        )
    return Agent(
        name="commute_agent",
        model=model or settings.gemini_model,
        description="Analyzes commute route duration, weather context, and delay risk.",
        instruction=COMMUTE_AGENT_INSTRUCTION,
        tools=tools,
        output_schema=CommuteAssessment,
        output_key="commute_assessment",
        disallow_transfer_to_parent=True,
        disallow_transfer_to_peers=True,
    )
