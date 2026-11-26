"""Simulation scenarios (A, B, C) for reliable offline/hackathon demonstrations."""

from __future__ import annotations

from typing import Literal

from app.api.schemas.analysis import AnalysisStartRequest, Coordinates, SimulationConfig


def build_simulation_request(
    scenario: Literal["scenario_a", "scenario_b", "scenario_c"],
) -> AnalysisStartRequest:
    """Build a preconfigured AnalysisStartRequest for Scenarios A, B, or C.

    - Scenario A: 9:00 AM important meeting, normal 25m route -> 50m (+25m simulated delay).
    - Scenario B: Flexible internal meeting affected; recommends rescheduling.
    - Scenario C: Rainy weather context without falsely claiming rain proves traffic.
    """
    origin = Coordinates(latitude=12.9716, longitude=77.5946, label="Home (Bengaluru)")
    destination = Coordinates(latitude=13.0306, longitude=77.5649, label="MSRIT Campus")

    if scenario == "scenario_a":
        sim = SimulationConfig(
            enabled=True,
            scenario="scenario_a",
            added_delay_minutes=25,
            weather_condition="Clear sky",
        )
    elif scenario == "scenario_b":
        sim = SimulationConfig(
            enabled=True,
            scenario="scenario_b",
            added_delay_minutes=20,
            weather_condition="Partly cloudy",
        )
    else:  # scenario_c
        sim = SimulationConfig(
            enabled=True,
            scenario="scenario_c",
            added_delay_minutes=15,
            weather_condition="Moderate rain",
        )

    return AnalysisStartRequest(
        origin=origin,
        destination=destination,
        required_arrival_time="09:00",
        departure_time="08:25",
        simulation=sim,
    )
