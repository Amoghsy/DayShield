"""Agent 3: Priority Agent using Google ADK + deterministic Python scoring."""

from __future__ import annotations

from google.adk import Agent
from google.adk.models.base_llm import BaseLlm

from app.agents.prompts import PRIORITY_AGENT_INSTRUCTION
from app.api.schemas.analysis import ImpactedEvent, PriorityAssessment
from app.config import get_settings
from app.services.priority_service import score_events


def compute_deterministic_priorities(events: list[dict]) -> list[dict]:
    """Compute transparent, deterministic 0-100 priority scores for impacted events.

    Args:
        events: List of ImpactedEvent dictionaries.

    Returns:
        Sorted list of scored event dictionaries.
    """
    parsed = [ImpactedEvent.model_validate(ev) for ev in events]
    return score_events(parsed)


def create_priority_agent(model: str | BaseLlm | None = None) -> Agent:
    """Create the Priority Agent (ADK Agent with structured PriorityAssessment output)."""
    settings = get_settings()
    return Agent(
        name="priority_agent",
        model=model or settings.gemini_model,
        description="Scores and ranks impacted calendar commitments using deterministic rules.",
        instruction=PRIORITY_AGENT_INSTRUCTION,
        tools=[compute_deterministic_priorities],
        output_schema=PriorityAssessment,
        output_key="priority_assessment",
        disallow_transfer_to_parent=True,
        disallow_transfer_to_peers=True,
    )
