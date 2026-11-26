"""SQLAlchemy ORM models for the 8 required DayShield tables."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    """1. Users table (minimal non-sensitive profile)."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    external_id: Mapped[str] = mapped_column(String(128), unique=True, default="demo_user")
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Kolkata")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class CalendarEventCache(Base):
    """2. Cached calendar events per analysis."""

    __tablename__ = "calendar_events_cache"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    analysis_id: Mapped[str] = mapped_column(String(36), ForeignKey("analyses.id"), index=True)
    event_id: Mapped[str] = mapped_column(String(256), index=True)
    title: Mapped[str] = mapped_column(String(256))
    start_time: Mapped[str] = mapped_column(String(64))
    end_time: Mapped[str] = mapped_column(String(64))
    data_source: Mapped[str] = mapped_column(String(32), default="sample")
    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Analysis(Base):
    """3. Multi-agent disruption analysis runs."""

    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), default="demo_user")
    status: Mapped[str] = mapped_column(String(32), default="running")
    simulation_mode: Mapped[bool] = mapped_column(Boolean, default=True)
    request_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    commute_assessment: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    schedule_assessment: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    priority_assessment: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    recovery_plan: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class AgentExecutionLog(Base):
    """4. Agent lifecycle logs (started, completed, failed, output)."""

    __tablename__ = "agent_execution_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    analysis_id: Mapped[str] = mapped_column(String(36), ForeignKey("analyses.id"), index=True)
    agent_name: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32))  # started | completed | failed
    message: Mapped[str] = mapped_column(Text, default="")
    output_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class RecoveryAction(Base):
    """5. Proposed & validated recovery actions."""

    __tablename__ = "recovery_actions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    analysis_id: Mapped[str] = mapped_column(String(36), ForeignKey("analyses.id"), index=True)
    action_id: Mapped[str] = mapped_column(String(64), index=True)
    action_type: Mapped[str] = mapped_column(String(64))
    event_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    description: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text, default="")
    parameters: Mapped[dict] = mapped_column(JSON, default=dict)
    data_source: Mapped[str] = mapped_column(String(32), default="simulated")
    validation_status: Mapped[str] = mapped_column(String(32), default="pending")  # valid | rejected
    validation_reason: Mapped[str] = mapped_column(Text, default="")
    approval_status: Mapped[str] = mapped_column(String(32), default="pending")  # pending | approved | rejected
    execution_status: Mapped[str] = mapped_column(String(32), default="not_executed")  # not_executed | executed | failed
    execution_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ApprovalRecord(Base):
    """6. One-time HMAC-bound approval tokens for approved actions."""

    __tablename__ = "approval_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    action_record_id: Mapped[str] = mapped_column(String(64), ForeignKey("recovery_actions.id"), index=True)
    decision: Mapped[str] = mapped_column(String(32))  # approved | rejected
    token_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True)
    parameters_hash: Mapped[str] = mapped_column(String(128))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consumed: Mapped[bool] = mapped_column(Boolean, default=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class AuditLog(Base):
    """7. Immutable audit trail of agent decisions, validations, approvals, and executions."""

    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    analysis_id: Mapped[str] = mapped_column(String(36), index=True)
    actor: Mapped[str] = mapped_column(String(64))  # agent name, validator, user, executor
    event_type: Mapped[str] = mapped_column(String(64))
    simulation_mode: Mapped[bool] = mapped_column(Boolean, default=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class IntegrationConnection(Base):
    """8. Integration connection metadata (no raw secret values stored)."""

    __tablename__ = "integration_connections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    provider: Mapped[str] = mapped_column(String(64), unique=True)
    connected: Mapped[bool] = mapped_column(Boolean, default=False)
    scopes: Mapped[list] = mapped_column(JSON, default=list)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
