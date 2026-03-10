"""Shared pytest fixtures for TGOps tests."""

from __future__ import annotations

import os
import tempfile
from unittest.mock import AsyncMock, MagicMock

import pytest

from tgops.core.audit import AuditLogger
from tgops.core.config import Settings


@pytest.fixture
def settings(tmp_path) -> Settings:
    """Settings fixture with test values — no real API credentials needed."""
    session_dir = tmp_path / "sessions"
    session_dir.mkdir(parents=True, exist_ok=True)
    jobs_dir = tmp_path / "jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)
    offboarding_dir = tmp_path / "offboarding"
    offboarding_dir.mkdir(parents=True, exist_ok=True)
    audit_path = str(tmp_path / "audit.jsonl")

    return Settings(
        api_id=12345,
        api_hash="test_hash_abc",
        phone="+10000000000",
        session_path=str(session_dir / "test_session"),
        audit_log_path=audit_path,
        jobs_dir=str(jobs_dir),
        offboarding_dir=str(offboarding_dir),
        dry_run=False,
        base_delay_seconds=0.01,   # Speed up tests
        emergency_delay_seconds=0.01,
    )


@pytest.fixture
def mock_client(settings) -> MagicMock:
    """Mock TGOpsClient that doesn't make real API calls."""
    from tgops.core.client import TGOpsClient

    client = MagicMock(spec=TGOpsClient)
    client._started = True
    client._settings = settings
    client.call = AsyncMock(return_value=None)
    client.start = AsyncMock()
    client.stop = AsyncMock()

    # Mock the underlying hydrogram client
    inner = MagicMock()
    client.client = inner
    return client


@pytest.fixture
def audit_logger(settings) -> AuditLogger:
    """AuditLogger using a temp file path from settings fixture."""
    return AuditLogger(settings.audit_log_path)


@pytest.fixture
def tmp_jobs_dir(tmp_path) -> str:
    """Temporary directory for migration job files."""
    jobs = tmp_path / "jobs"
    jobs.mkdir(parents=True, exist_ok=True)
    return str(jobs)
