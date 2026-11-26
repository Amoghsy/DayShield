"""Phase 2 tests: OSRM, Open-Meteo, FastMCP tools, McpToolset, and Simulation Scenarios."""

from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient
from google.adk.tools.mcp_tool import McpToolset

from app.agents.commute_agent import create_commute_agent, get_commute_route_and_weather
from app.agents.schedule_agent import create_schedule_agent
from app.agents.workflow import run_analysis_workflow
from app.integrations.osrm_client import OSRMClient
from app.integrations.weather_client import WeatherClient
from app.main import app
from app.mcp_servers.server import mcp
from app.mcp_servers.tools.email import create_email_draft
from app.services.simulation_service import build_simulation_request
from tests.test_phase1_workflow import MockDayShieldLlm


@pytest.mark.asyncio
async def test_osrm_client_success_and_disclaimer(monkeypatch):
    """Verify OSRMClient parses routes and labels data_source='estimated' (not live traffic)."""

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "code": "Ok",
                "routes": [
                    {"duration": 1680.0, "distance": 12400.0},
                    {"duration": 1920.0, "distance": 14100.0},
                ],
            }

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url, params=None):
            return FakeResponse()

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)

    client = OSRMClient()
    res = await client.get_routes(12.9716, 77.5946, 13.0306, 77.5649)
    assert res["ok"] is True
    assert res["data_source"] == "estimated"
    assert "NOT live traffic" in res["disclaimer"]
    assert res["primary_route"]["duration_minutes"] == 28
    assert len(res["routes"]) == 2


@pytest.mark.asyncio
async def test_osrm_client_handles_failure(monkeypatch):
    """Verify OSRMClient handles HTTP/network errors gracefully."""

    class FailingAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url, params=None):
            raise httpx.ConnectError("Network unreachable")

    monkeypatch.setattr(httpx, "AsyncClient", FailingAsyncClient)

    client = OSRMClient()
    res = await client.get_routes(12.9716, 77.5946, 13.0306, 77.5649)
    assert res["ok"] is False
    assert res["data_source"] == "estimated"
    assert "OSRM service unavailable" in res["error"]


@pytest.mark.asyncio
async def test_weather_client_success(monkeypatch):
    """Verify WeatherClient parses Open-Meteo current weather."""

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "current": {
                    "temperature_2m": 23.5,
                    "precipitation": 1.2,
                    "weather_code": 61,
                    "wind_speed_10m": 11.0,
                }
            }

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url, params=None):
            return FakeResponse()

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)

    client = WeatherClient()
    res = await client.get_current_weather(12.9716, 77.5946)
    assert res["ok"] is True
    assert res["data_source"] == "live"
    assert res["condition"] == "Light rain"


@pytest.mark.asyncio
async def test_fastmcp_server_registers_all_tools():
    """Verify all 9 required MCP tools are registered on the FastMCP server."""
    tools = await mcp.list_tools()
    tool_names = {t.name for t in tools}
    assert tool_names == {
        "get_route",
        "get_alternative_routes",
        "calculate_route_duration",
        "get_current_weather",
        "get_weather_forecast",
        "get_today_events",
        "get_event_details",
        "get_available_slots",
        "create_email_draft",
    }

    draft = create_email_draft("user@example.com", "Late notice", "Running 15m late.")
    assert draft["sent"] is False
    assert draft["status"] == "draft_prepared"


def test_adk_agents_attach_mcptoolset():
    """Verify Commute and Schedule agents attach McpToolset when use_mcp=True."""
    commute = create_commute_agent(use_mcp=True)
    schedule = create_schedule_agent(use_mcp=True)
    assert any(isinstance(t, McpToolset) for t in commute.tools)
    assert any(isinstance(t, McpToolset) for t in schedule.tools)


@pytest.mark.asyncio
async def test_simulation_scenarios_a_b_c():
    """Verify Simulation Scenarios A, B, and C produce clearly labeled simulated outputs."""
    req_a = build_simulation_request("scenario_a")
    res_a = await get_commute_route_and_weather(
        req_a.origin.latitude,
        req_a.origin.longitude,
        req_a.destination.latitude,
        req_a.destination.longitude,
        simulation_enabled=req_a.simulation.enabled,
        added_delay_minutes=req_a.simulation.added_delay_minutes,
        weather_condition=req_a.simulation.weather_condition,
    )
    assert res_a["data_source"] == "simulated"
    assert res_a["delay_minutes"] == 25
    assert res_a["estimated_travel_minutes"] == 50

    req_c = build_simulation_request("scenario_c")
    assert "rain" in req_c.simulation.weather_condition.lower()


def test_simulation_run_endpoint(monkeypatch):
    """Verify POST /api/simulation/run?scenario=scenario_b returns 200 and simulation_mode=True."""
    mock_llm = MockDayShieldLlm(call_log=[])

    async def _mock_run(request, analysis_id=None, event_callback=None):
        return await run_analysis_workflow(request, analysis_id=analysis_id, model=mock_llm, event_callback=event_callback)

    monkeypatch.setattr("app.api.routes.simulation.run_analysis_workflow", _mock_run)

    client = TestClient(app)
    resp = client.post("/api/simulation/run", json={"scenario": "scenario_b"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["simulation_mode"] is True
    assert data["status"] == "completed"
