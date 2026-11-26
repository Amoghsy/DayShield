"""Phase 1 tests: ADK Workflow orchestration, deterministic priority scoring, and FastAPI."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types

from app.agents.priority_agent import compute_deterministic_priorities
from app.agents.workflow import build_dayshield_workflow, run_analysis_workflow
from app.api.schemas.analysis import (
    AnalysisStartRequest,
    CommuteAssessment,
    ImpactedEvent,
    PriorityAssessment,
    RecoveryPlan,
    ScheduleAssessment,
    SimulationConfig,
)
from app.main import app
from app.services.priority_service import score_events


class MockDayShieldLlm(BaseLlm):
    """Deterministic BaseLlm stub for testing Google ADK Workflow without API keys."""

    model: str = "mock-gemini-2.5-flash"
    call_log: list[str] = []

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        sys_text = ""
        if llm_request.config and llm_request.config.system_instruction:
            sys_text = str(llm_request.config.system_instruction)

        # Identify which of the 4 agents is calling based on its instruction
        if "Commute Agent" in sys_text:
            self.call_log.append("commute_agent")
            await asyncio.sleep(0.02)
            payload = CommuteAssessment(
                status="disrupted",
                estimated_travel_minutes=50,
                baseline_travel_minutes=25,
                delay_minutes=25,
                recommended_route="route_outer_ring_alt_sim",
                alternative_routes=["route_outer_ring_alt_sim", "route_bellary_rd_sim"],
                weather_context="Moderate rain (simulated)",
                data_source="simulated",
                confidence=0.92,
                reasoning_summary="Simulated 25-minute delay due to scenario_a.",
            ).model_dump_json()
        elif "Schedule Agent" in sys_text:
            self.call_log.append("schedule_agent")
            await asyncio.sleep(0.02)
            payload = ScheduleAssessment(
                impacted_events=[
                    ImpactedEvent(
                        event_id="sample_evt_101",
                        title="Client Project Review",
                        start_time="09:00",
                        end_time="10:00",
                        location="MSRIT Innovation Lab",
                        attendees=["client.lead@acmecorp.com"],
                        has_external_attendees=True,
                        is_online=False,
                        can_join_online=True,
                        minutes_late=25,
                        impact_level="high",
                        event_category="client_meeting",
                    )
                ],
                free_slots=[],
                data_source="sample",
                schedule_summary="One client meeting is impacted by 25 minutes.",
            ).model_dump_json()
        elif "Priority Agent" in sys_text:
            self.call_log.append("priority_agent")
            scored = compute_deterministic_priorities(
                [
                    {
                        "event_id": "sample_evt_101",
                        "title": "Client Project Review",
                        "start_time": "09:00",
                        "end_time": "10:00",
                        "location": "MSRIT Innovation Lab",
                        "attendees": ["client.lead@acmecorp.com"],
                        "has_external_attendees": True,
                        "is_online": False,
                        "can_join_online": True,
                        "minutes_late": 25,
                        "impact_level": "high",
                        "event_category": "client_meeting",
                    }
                ]
            )
            payload = PriorityAssessment(
                ranked_events=[
                    {
                        "event_id": scored[0]["event_id"],
                        "title": scored[0]["title"],
                        "priority_score": scored[0]["priority_score"],
                        "priority": scored[0]["priority"],
                        "recommended_handling": scored[0]["recommended_handling"],
                        "reason": "External client commitment with high lateness impact.",
                    }
                ]
            ).model_dump_json()
        else:
            self.call_log.append("recovery_agent")
            payload = RecoveryPlan(
                recovery_plan=[
                    {
                        "action_id": "action_001",
                        "action_type": "create_email_draft",
                        "event_id": "sample_evt_101",
                        "description": "Draft delay notice to client.lead@acmecorp.com",
                        "reason": "User is estimated 25 minutes late.",
                        "parameters": {
                            "recipient": "client.lead@acmecorp.com",
                            "subject": "Running ~25 mins late for Client Project Review",
                        },
                        "requires_approval": True,
                    },
                    {
                        "action_id": "action_002",
                        "action_type": "suggest_online_join",
                        "event_id": "sample_evt_101",
                        "description": "Suggest joining Client Project Review online.",
                        "reason": "Online join avoids full 25-minute commute delay.",
                        "parameters": {"event_id": "sample_evt_101"},
                        "requires_approval": True,
                    },
                ],
                summary="Proposed email draft and online-join option pending user approval.",
            ).model_dump_json()

        yield LlmResponse(
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(text=payload)],
            ),
            partial=False,
        )


def test_deterministic_priority_scoring():
    """Verify deterministic scoring orders examination > interview > client > internal > personal."""
    events = [
        ImpactedEvent(
            event_id="e_personal",
            title="Gym",
            start_time="17:00",
            end_time="18:00",
            event_category="personal_task",
            minutes_late=20,
        ),
        ImpactedEvent(
            event_id="e_exam",
            title="Final Exam",
            start_time="09:00",
            end_time="11:00",
            event_category="examination",
            minutes_late=15,
        ),
        ImpactedEvent(
            event_id="e_internal",
            title="Team Sync",
            start_time="10:00",
            end_time="10:30",
            event_category="internal_meeting",
            can_join_online=True,
            minutes_late=10,
        ),
    ]
    ranked = score_events(events)
    assert [r["event_id"] for r in ranked] == ["e_exam", "e_internal", "e_personal"]
    assert ranked[0]["priority_score"] == 100
    assert ranked[0]["priority"] == "critical"


def test_workflow_graph_structure():
    """Verify ADK Workflow graph has the 4 agents + join + merge nodes."""
    mock_llm = MockDayShieldLlm()
    wf = build_dayshield_workflow(model=mock_llm)
    node_names = {n.name for n in wf.graph.nodes}
    assert {
        "commute_agent",
        "schedule_agent",
        "impact_join",
        "impact_merge",
        "priority_agent",
        "recovery_agent",
    }.issubset(node_names)


@pytest.mark.asyncio
async def test_adk_workflow_end_to_end_parallel_and_sequential():
    """Run the full ADK Workflow with MockDayShieldLlm and verify ordering & outputs."""
    mock_llm = MockDayShieldLlm(call_log=[])
    req = AnalysisStartRequest(
        simulation=SimulationConfig(enabled=True, scenario="scenario_a", added_delay_minutes=25)
    )

    result = await run_analysis_workflow(req, model=mock_llm)

    assert result.status == "completed", f"Workflow failed: {result.error}"
    assert result.simulation_mode is True
    assert result.commute_assessment is not None
    assert result.commute_assessment.delay_minutes == 25
    assert result.commute_assessment.data_source == "simulated"

    assert result.schedule_assessment is not None
    assert len(result.schedule_assessment.impacted_events) == 1
    assert result.schedule_assessment.data_source == "sample"

    assert result.priority_assessment is not None
    assert result.priority_assessment.ranked_events[0].priority_score >= 90

    assert result.recovery_plan is not None
    assert len(result.recovery_plan.recovery_plan) == 2
    assert all(a.requires_approval for a in result.recovery_plan.recovery_plan)

    # Verify commute & schedule ran before priority, and priority ran before recovery
    assert set(mock_llm.call_log[:2]) == {"commute_agent", "schedule_agent"}
    assert mock_llm.call_log[2:] == ["priority_agent", "recovery_agent"]


def test_fastapi_health_and_docs():
    """Verify FastAPI /health and Swagger /docs endpoints."""
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"

    docs_resp = client.get("/docs")
    assert docs_resp.status_code == 200


def test_fastapi_analysis_start_endpoint(monkeypatch):
    """Verify POST /api/analysis/start and GET /api/analysis/{id} via TestClient."""
    mock_llm = MockDayShieldLlm(call_log=[])

    async def _mock_run(request: AnalysisStartRequest, analysis_id: str | None = None, event_callback=None):
        return await run_analysis_workflow(request, analysis_id=analysis_id, model=mock_llm, event_callback=event_callback)

    monkeypatch.setattr("app.api.routes.analysis.run_analysis_workflow", _mock_run)

    client = TestClient(app)
    resp = client.post(
        "/api/analysis/start",
        json={"simulation": {"enabled": True, "scenario": "scenario_a", "added_delay_minutes": 25}},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "completed"
    aid = body["analysis_id"]

    get_resp = client.get(f"/api/analysis/{aid}")
    assert get_resp.status_code == 200
    assert get_resp.json()["analysis_id"] == aid
