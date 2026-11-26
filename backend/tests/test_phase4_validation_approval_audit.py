"""Phase 4 tests: Deterministic validator, HMAC approval tokens, execution gate, and audit log."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.agents.workflow import run_analysis_workflow
from app.api.schemas.analysis import (
    CommuteAssessment,
    ImpactedEvent,
    PriorityAssessment,
    ProposedRecoveryAction,
    RankedEvent,
    ScheduleAssessment,
)
from app.database.database import SessionLocal
from app.database.models import RecoveryAction
from app.main import app
from app.services.validation_service import validate_action
from app.utils.security import generate_approval_token, verify_approval_token
from tests.test_phase1_workflow import MockDayShieldLlm


def _sample_context():
    commute = CommuteAssessment(
        status="disrupted",
        estimated_travel_minutes=50,
        baseline_travel_minutes=25,
        delay_minutes=25,
        recommended_route="route_a",
        alternative_routes=["route_a", "route_b"],
        weather_context="Clear",
        data_source="simulated",
        confidence=0.9,
        reasoning_summary="25m delay",
    )
    schedule = ScheduleAssessment(
        impacted_events=[
            ImpactedEvent(
                event_id="evt_crit",
                title="Final Exam",
                start_time="09:00",
                end_time="10:00",
                event_category="examination",
                minutes_late=25,
            ),
            ImpactedEvent(
                event_id="evt_flex",
                title="Gym",
                start_time="11:00",
                end_time="12:00",
                event_category="personal_task",
                minutes_late=10,
            ),
        ],
        free_slots=[],
        data_source="sample",
        schedule_summary="2 events",
    )
    priority = PriorityAssessment(
        ranked_events=[
            RankedEvent(
                event_id="evt_crit",
                title="Final Exam",
                priority_score=100,
                priority="critical",
                recommended_handling="protect",
                reason="Exam",
            ),
            RankedEvent(
                event_id="evt_flex",
                title="Gym",
                priority_score=35,
                priority="low",
                recommended_handling="reschedule",
                reason="Flexible",
            ),
        ]
    )
    return commute, schedule, priority


def test_validator_rejects_unsafe_actions():
    """Verify deterministic validator blocks non-existent events, protected reschedules, conflicts, bad routes, and bad emails."""
    commute, schedule, priority = _sample_context()

    # 1. Non-existent event
    res1 = validate_action(
        ProposedRecoveryAction(
            action_id="a1",
            action_type="suggest_online_join",
            event_id="evt_missing",
            description="Join online",
            reason="Test",
        ),
        commute,
        schedule,
        priority,
    )
    assert res1.valid is False

    # 2. Reschedule protected/critical event
    res2 = validate_action(
        ProposedRecoveryAction(
            action_id="a2",
            action_type="reschedule_event",
            event_id="evt_crit",
            description="Move exam",
            reason="Test",
            parameters={"new_start_time": "14:00", "new_end_time": "15:00"},
        ),
        commute,
        schedule,
        priority,
    )
    assert res2.valid is False
    assert "protected" in res2.reason.lower()

    # 3. Outside working hours
    res3 = validate_action(
        ProposedRecoveryAction(
            action_id="a3",
            action_type="reschedule_event",
            event_id="evt_flex",
            description="Move gym to 5am",
            reason="Test",
            parameters={"new_start_time": "05:00", "new_end_time": "06:00"},
        ),
        commute,
        schedule,
        priority,
    )
    assert res3.valid is False
    assert "working hours" in res3.reason.lower()

    # 4. Conflict with existing event
    res4 = validate_action(
        ProposedRecoveryAction(
            action_id="a4",
            action_type="reschedule_event",
            event_id="evt_flex",
            description="Move gym to 09:30",
            reason="Test",
            parameters={"new_start_time": "09:30", "new_end_time": "10:30"},
        ),
        commute,
        schedule,
        priority,
    )
    assert res4.valid is False
    assert "conflicts" in res4.reason.lower()

    # 5. Unverified route
    res5 = validate_action(
        ProposedRecoveryAction(
            action_id="a5",
            action_type="switch_route",
            description="Take secret route",
            reason="Test",
            parameters={"route_id": "hallucinated_route"},
        ),
        commute,
        schedule,
        priority,
    )
    assert res5.valid is False

    # 6. Invalid email recipient
    res6 = validate_action(
        ProposedRecoveryAction(
            action_id="a6",
            action_type="create_email_draft",
            description="Draft email",
            reason="Test",
            parameters={"recipient": "not-an-email"},
        ),
        commute,
        schedule,
        priority,
    )
    assert res6.valid is False


def test_approval_token_binding_and_expiry():
    """Verify HMAC token rejects tampered parameters, wrong action IDs, and expired tokens."""
    params = {"recipient": "client@acmecorp.com", "subject": "Late"}
    raw_token, _, _, _ = generate_approval_token("act_1", params, ttl_seconds=60)

    ok, _ = verify_approval_token(raw_token, "act_1", params)
    assert ok is True

    # Tampered parameters
    ok_param, _ = verify_approval_token(raw_token, "act_1", {"recipient": "evil@attacker.com"})
    assert ok_param is False

    # Wrong action ID
    ok_id, _ = verify_approval_token(raw_token, "act_2", params)
    assert ok_id is False

    # Expired token
    expired_token, _, _, _ = generate_approval_token("act_1", params, ttl_seconds=-5)
    ok_exp, _ = verify_approval_token(expired_token, "act_1", params)
    assert ok_exp is False


def test_end_to_end_approval_execution_and_duplicate_prevention(monkeypatch):
    """Full flow: start analysis -> approve -> execute once -> block duplicate & unapproved."""
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

        rec_resp = client.get(f"/api/recovery/{aid}")
        assert rec_resp.status_code == 200
        actions = rec_resp.json()["actions"]
        assert len(actions) == 2
        action_0_id = actions[0]["id"]
        action_1_id = actions[1]["id"]

        # Unapproved execution must fail with 403
        unapproved_exec = client.post(
            "/api/actions/execute-approved",
            json={"action_id": action_0_id, "approval_token": "fake:token:1:2:3"},
        )
        assert unapproved_exec.status_code == 403

        # Approve action 0 -> returns one-time token
        approve_resp = client.post(f"/api/approval/{action_0_id}/approve")
        assert approve_resp.status_code == 200
        token = approve_resp.json()["approval_token"]

        # Execute approved action 0 -> succeeds
        exec_resp = client.post(
            "/api/actions/execute-approved",
            json={"action_id": action_0_id, "approval_token": token},
        )
        assert exec_resp.status_code == 200
        assert exec_resp.json()["execution_status"] == "executed"

        # Duplicate execution with same token -> rejected (403)
        dup_resp = client.post(
            "/api/actions/execute-approved",
            json={"action_id": action_0_id, "approval_token": token},
        )
        assert dup_resp.status_code == 403

        # Reject action 1 -> cannot be executed
        rej_resp = client.post(
            f"/api/approval/{action_1_id}/reject",
            json={"reason": "User prefers in-person"},
        )
        assert rej_resp.status_code == 200
        assert rej_resp.json()["approval_status"] == "rejected"

        # Audit trail contains validation, approval, execution, and rejection
        audit_resp = client.get(f"/api/audit/{aid}")
        assert audit_resp.status_code == 200
        event_types = [e["event_type"] for e in audit_resp.json()["audit_logs"]]
        assert "action_validated" in event_types
        assert "action_approved" in event_types
        assert "action_executed" in event_types
        assert "action_rejected" in event_types
