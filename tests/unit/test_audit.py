"""Tests for tgops.core.audit."""

from __future__ import annotations

import json
from datetime import datetime

import pytest

from tgops.core.audit import AuditEntry, AuditLogger


class TestAuditEntry:
    def test_to_dict_serializes_timestamp(self):
        """AuditEntry.to_dict() converts timestamp to ISO string."""
        entry = AuditEntry(event="test.event", timestamp=datetime(2026, 1, 1, 12, 0, 0))
        d = entry.to_dict()
        assert d["event"] == "test.event"
        assert isinstance(d["timestamp"], str)
        assert "2026-01-01" in d["timestamp"]

    def test_from_dict_parses_timestamp(self):
        """AuditEntry.from_dict() parses ISO timestamp string back to datetime."""
        d = {
            "event": "test.event",
            "timestamp": "2026-01-01T12:00:00",
            "job_id": None,
            "group_id": None,
            "user_id": None,
            "step": None,
            "status": None,
            "details": {},
        }
        entry = AuditEntry.from_dict(d)
        assert entry.event == "test.event"
        assert isinstance(entry.timestamp, datetime)
        assert entry.timestamp.year == 2026

    def test_roundtrip(self):
        """AuditEntry can be serialized and deserialized losslessly."""
        entry = AuditEntry(
            event="migration.step.snapshot",
            job_id="job-123",
            group_id=456,
            user_id=789,
            step="snapshot",
            status="completed",
            details={"title": "My Group"},
        )
        d = entry.to_dict()
        restored = AuditEntry.from_dict(d)
        assert restored.event == entry.event
        assert restored.job_id == entry.job_id
        assert restored.group_id == entry.group_id
        assert restored.details == entry.details


class TestAuditLogger:
    @pytest.mark.asyncio
    async def test_log_creates_file(self, audit_logger, tmp_path):
        """Logging an entry creates the JSONL file."""
        import os

        entry = AuditEntry(event="test.create")
        await audit_logger.log(entry)
        assert os.path.isfile(audit_logger.log_path)

    @pytest.mark.asyncio
    async def test_log_appends(self, audit_logger):
        """Multiple log calls append multiple lines."""
        await audit_logger.log(AuditEntry(event="first"))
        await audit_logger.log(AuditEntry(event="second"))
        await audit_logger.log(AuditEntry(event="third"))

        with open(audit_logger.log_path) as f:
            lines = [l.strip() for l in f if l.strip()]
        assert len(lines) == 3

    @pytest.mark.asyncio
    async def test_log_is_valid_jsonl(self, audit_logger):
        """Each line in the log is valid JSON."""
        await audit_logger.log(AuditEntry(event="ev1", group_id=100))
        await audit_logger.log(AuditEntry(event="ev2", user_id=200))

        with open(audit_logger.log_path) as f:
            lines = [l.strip() for l in f if l.strip()]

        for line in lines:
            data = json.loads(line)
            assert "event" in data
            assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_read_entries_empty(self, audit_logger):
        """Reading from a non-existent file returns empty list."""
        entries = await audit_logger.read_entries()
        assert entries == []

    @pytest.mark.asyncio
    async def test_read_entries_returns_all(self, audit_logger):
        """read_entries() returns all logged entries."""
        for i in range(5):
            await audit_logger.log(AuditEntry(event=f"event.{i}"))

        entries = await audit_logger.read_entries()
        assert len(entries) == 5
        assert entries[0].event == "event.0"
        assert entries[-1].event == "event.4"

    @pytest.mark.asyncio
    async def test_read_entries_with_limit(self, audit_logger):
        """read_entries(limit=N) returns only the last N entries."""
        for i in range(10):
            await audit_logger.log(AuditEntry(event=f"event.{i}"))

        entries = await audit_logger.read_entries(limit=3)
        assert len(entries) == 3
        assert entries[-1].event == "event.9"

    @pytest.mark.asyncio
    async def test_append_only_preserves_existing(self, audit_logger):
        """Log is append-only — existing entries are not overwritten."""
        await audit_logger.log(AuditEntry(event="first"))

        # Create a second logger pointing at the same file
        second_logger = AuditLogger(audit_logger.log_path)
        await second_logger.log(AuditEntry(event="second"))

        entries = await audit_logger.read_entries()
        assert len(entries) == 2
        assert entries[0].event == "first"
        assert entries[1].event == "second"
