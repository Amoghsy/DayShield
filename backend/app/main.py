"""FastAPI application entrypoint for DayShield backend."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.actions import router as actions_router
from app.api.routes.analysis import router as analysis_router
from app.api.routes.approval import router as approval_router
from app.api.routes.calendar import router as calendar_router
from app.api.routes.integrations import router as integrations_router
from app.api.routes.simulation import router as simulation_router
from app.config import get_settings
from app.database.database import init_db

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Initialize SQLite tables on application startup."""
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Approval-first, multi-agent schedule recovery backend powered by Google ADK."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analysis_router)
app.include_router(approval_router)
app.include_router(actions_router)
app.include_router(calendar_router)
app.include_router(integrations_router)
app.include_router(simulation_router)


@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "simulation_mode": settings.simulation_mode,
        "model": settings.gemini_model,
    }
