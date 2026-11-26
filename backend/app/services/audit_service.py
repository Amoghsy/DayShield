"""Audit logging service backed by SQLite."""

from __future__ import annotations

from typing import Any
from sqlalchemy.orm import Session

from app.database.models import AuditLog


def record_audit(
    db: Session,
    *,
    analysis_id: str,
    actor: str,
    event_type: str,
    simulation_mode: bool,
    details: dict[str, Any] | None = None,
) -> AuditLog:
    """Append an immutable audit log entry to the database."""
    entry = AuditLog(
        analysis_id=analysis_id,
        actor=actor,
        event_type=event_type,
        simulation_mode=simulation_mode,
        details=details or {},
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def get_audit_trail(db: Session, analysis_id: str) -> list[AuditLog]:
    """Return chronological audit logs for an analysis."""
    return (
        db.query(AuditLog)
        .filter(AuditLog.analysis_id == analysis_id)
        .order_by(AuditLog.created_at.asc())
        .all()
    )
