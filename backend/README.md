# DayShield Backend

Approval-first, multi-agent schedule recovery backend built with **FastAPI**, **Google ADK (`google.adk.Workflow`)**, **FastMCP**, **SQLite/SQLAlchemy**, **OSRM**, **Open-Meteo**, and **Google Calendar / Gmail Drafts**.

## Architecture

```
START
  |---> commute_agent  (OSRM + Open-Meteo / Simulation) ---|
  |---> schedule_agent (Google Calendar / Sample)        --|--> JoinNode --> impact_merge --> priority_agent --> recovery_agent
                                                                                                                  |
                                                                                                                  v
                                                                                                     Deterministic Validator
                                                                                                                  |
                                                                                                                  v
                                                                                                       User Approval Gate (HMAC)
                                                                                                                  |
                                                                                                                  v
                                                                                                      Action Executor & Audit Log
```

## Quick Start

1. **Create and activate a virtual environment (recommended):**
   ```powershell
   cd backend
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure environment variables:**
   ```powershell
   copy .env.example .env
   ```
   Set `GEMINI_API_KEY` (from Google AI Studio) to run live Gemini 2.5 Flash reasoning. Leave Google OAuth blank to demo safely in simulation/sample mode.

3. **Run the FastAPI server:**
   ```powershell
   uvicorn app.main:app --reload
   ```
   - Swagger UI: `http://localhost:8000/docs`
   - Health check: `http://localhost:8000/health`

4. **Run the standalone FastMCP tools server (optional):**
   ```powershell
   python -m app.mcp_servers.server
   ```

## Free Google OAuth 2.0 Setup (No Billing Required)

1. Go to [Google Cloud Console](https://console.cloud.google.com/) and create a free project (no billing account needed).
2. Enable **Google Calendar API** and **Gmail API**.
3. Configure the **OAuth consent screen** (External, add your email as a Test User).
4. Create **OAuth 2.0 Client ID** (Web application) with redirect URI:
   `http://localhost:8000/api/integrations/google/callback`
5. Add `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` to `.env`.
6. DayShield requests only `calendar.readonly` and `gmail.compose` (draft creation only — automatic sending is disabled).

## Simulation Demo Scenarios

- `POST /api/simulation/run` with `{"scenario": "scenario_a"}` — 9:00 AM meeting with a 25-minute simulated commute delay.
- `POST /api/simulation/run` with `{"scenario": "scenario_b"}` — Flexible internal meeting recommended for rescheduling.
- `POST /api/simulation/run` with `{"scenario": "scenario_c"}` — Rainy weather context without falsely claiming rain proves traffic.

## Running Tests

```powershell
cd backend
pytest -v
```
