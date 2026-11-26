"""Agent 4: Recovery Agent using Google ADK."""

from __future__ import annotations

from google.adk import Agent
from google.adk.models.base_llm import BaseLlm

from app.agents.prompts import RECOVERY_AGENT_INSTRUCTION
from app.api.schemas.analysis import RecoveryPlan
from app.config import get_settings


def create_recovery_agent(model: str | BaseLlm | None = None) -> Agent:
    """Create the Recovery Agent (ADK Agent with structured RecoveryPlan output).

    Note: The Recovery Agent ONLY proposes actions. It has no write tools and
    cannot modify calendar events or send emails.
    """
    settings = get_settings()
    return Agent(
        name="recovery_agent",
        model=model or settings.gemini_model,
        description="Generates an approval-first, conflict-free recovery plan.",
        instruction=RECOVERY_AGENT_INSTRUCTION,
        tools=[],
        output_schema=RecoveryPlan,
        output_key="recovery_plan",
        disallow_transfer_to_parent=True,
        disallow_transfer_to_peers=True,
    )
