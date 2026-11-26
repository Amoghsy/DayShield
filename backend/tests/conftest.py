"""Pytest configuration ensuring SQLite tables are initialized for API tests."""

from __future__ import annotations

import pytest

from app.database.database import init_db


@pytest.fixture(autouse=True, scope="session")
def _setup_database():
    """Initialize SQLite schema before running tests."""
    init_db()
