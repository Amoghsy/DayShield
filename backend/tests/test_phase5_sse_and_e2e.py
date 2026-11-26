"""Phase 5 tests: Agent status endpoint, SSE streaming, and Swagger/OpenAPI completeness."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.agents.workflow import run_analysis_workflow
from app.main import app
from tests.test_phase1_workflow import MockDayShieldLlm


def test_openapi_contains_all_required_endpoints():
    """Verify Swagger/OpenAPI schema exposes every required DayShield endpoint."""
    with TestClient(app) as client:
        schema = client.get("/openapi.json").json()
        paths = set(schema["paths"].keys())

        required = {
            "/health",
            "/api/analysis/start",
            "/api/analysis/{analysis_id}",
            "/api/agents/status/{analysis_id}",
            "/api/agents/stream/{analysis_id}",
            "/api/recovery/{analysis_id}",
            "/api/approval/{action_id}/approve",
            "/api/approval/{action_id}/reject",
            "/api/actions/execute-approved",
            "/api/audit/{analysis_id}",
            "/api/calendar/today",
            "/api/integrations/status",
            "/api/simulation/run",
        }
        missing = required - paths
        assert not missing, f"Missing endpoints in OpenAPI: {missing}"


def test_agent_status_and_sse_stream(monkeypatch):
    """Verify GET /api/agents/status/{id} and SSE GET /api/agents/stream/{id}."""
    mock_llm = MockDayShieldLlm(call_log=[])

    async def _mock_run(request, analysis_id=None, event_callback=None):
        return await run_analysis_workflow(
            request,
            analysis_id=analysis_id,
            model=mock_llm,
            event_callback=event_callback,
        )

    monkeypatch.setattr("app.api.routes.analysis.run_analysis_workflow", _mock_run)

    with TestClient(app) as client:
        start_resp = client.post(
            "/api/analysis/start",
            json={"simulation": {"enabled": True, "scenario": "scenario_a", "added_delay_minutes": 25}},
        )
        assert start_resp.status_code == 200
        aid = start_resp.json()["analysis_id"]

        status_resp = client.get(f"/api/agents/status/{aid}")
        assert status_resp.status_code == 200
        agents = status_resp.json()["agents"]
        assert len(agents) == 5
        assert all(a["status"] == "completed" for a in agents)

        stream_resp = client.get(f"/api/agents/stream/{aid}")
        assert stream_resp.status_code == 200
        assert "text/event-stream" in stream_resp.headers["content-type"]
        body = stream_resp.text
        assert "event: agent_update" in body
        assert "commute_agent" in body
        assert "event: complete" in body
