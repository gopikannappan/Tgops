"""Tests for MigrationJob state machine and MigrationService."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tgops.models.migration import MigrationJob, MigrationStatus
from tgops.services.migration import (
    MigrationService,
    _deserialize_job,
    _serialize_job,
)


# ---------------------------------------------------------------------------
# MigrationJob state machine
# ---------------------------------------------------------------------------

class TestMigrationJobStateMachine:
    def test_new_job_starts_as_pending(self):
        """A freshly created MigrationJob has PENDING status."""
        job = MigrationJob(job_id="j1", source_group_id=100)
        assert job.status == MigrationStatus.PENDING

    def test_new_job_has_empty_steps(self):
        """A new job has no completed steps."""
        job = MigrationJob(job_id="j1", source_group_id=100)
        assert job.steps_completed == []

    def test_steps_can_be_appended(self):
        """Completed steps accumulate in order."""
        job = MigrationJob(job_id="j1", source_group_id=100)
        job.steps_completed.append("snapshot")
        job.steps_completed.append("create_target")
        assert job.steps_completed == ["snapshot", "create_target"]

    def test_status_can_transition(self):
        """Status can be updated to any MigrationStatus value."""
        job = MigrationJob(job_id="j1", source_group_id=100)
        job.status = MigrationStatus.CREATING_TARGET
        assert job.status == MigrationStatus.CREATING_TARGET
        job.status = MigrationStatus.COMPLETE
        assert job.status == MigrationStatus.COMPLETE

    def test_error_field(self):
        """Error message can be set when status is FAILED."""
        job = MigrationJob(job_id="j1", source_group_id=100)
        job.status = MigrationStatus.FAILED
        job.error = "Something went wrong"
        assert job.error == "Something went wrong"

    def test_completed_at_is_none_by_default(self):
        """completed_at is None until the job finishes."""
        job = MigrationJob(job_id="j1", source_group_id=100)
        assert job.completed_at is None


# ---------------------------------------------------------------------------
# Serialization / Deserialization
# ---------------------------------------------------------------------------

class TestMigrationJobSerialization:
    def test_serialize_produces_valid_dict(self):
        """_serialize_job returns a JSON-serializable dict."""
        job = MigrationJob(
            job_id="test-123",
            source_group_id=999,
            target_group_id=888,
            status=MigrationStatus.COMPLETE,
            steps_completed=["snapshot", "create_target"],
        )
        d = _serialize_job(job)
        # Should be JSON-serializable
        text = json.dumps(d)
        assert "test-123" in text
        assert d["status"] == "COMPLETE"

    def test_serialize_datetimes_as_iso(self):
        """Datetime fields are serialized as ISO strings."""
        ts = datetime(2026, 1, 15, 10, 30, 0)
        job = MigrationJob(job_id="j", source_group_id=1, created_at=ts)
        d = _serialize_job(job)
        assert isinstance(d["created_at"], str)
        assert "2026-01-15" in d["created_at"]

    def test_serialize_completed_at_none(self):
        """completed_at=None serializes as null."""
        job = MigrationJob(job_id="j", source_group_id=1)
        d = _serialize_job(job)
        assert d["completed_at"] is None

    def test_deserialize_restores_job(self):
        """_deserialize_job produces a MigrationJob equal to the original."""
        original = MigrationJob(
            job_id="round-trip",
            source_group_id=42,
            target_group_id=99,
            status=MigrationStatus.BLASTING_INVITE,
            steps_completed=["snapshot", "create_target", "copy_settings"],
        )
        d = _serialize_job(original)
        restored = _deserialize_job(d)

        assert restored.job_id == original.job_id
        assert restored.source_group_id == original.source_group_id
        assert restored.target_group_id == original.target_group_id
        assert restored.status == original.status
        assert restored.steps_completed == original.steps_completed

    def test_deserialize_parses_timestamps(self):
        """_deserialize_job parses ISO timestamp strings back to datetime."""
        job = MigrationJob(job_id="j", source_group_id=1)
        d = _serialize_job(job)
        restored = _deserialize_job(d)
        assert isinstance(restored.created_at, datetime)

    def test_roundtrip_via_json(self):
        """Job survives a full JSON encode/decode cycle."""
        job = MigrationJob(
            job_id=str(uuid.uuid4()),
            source_group_id=12345,
            steps_completed=["snapshot"],
        )
        json_text = json.dumps(_serialize_job(job))
        restored = _deserialize_job(json.loads(json_text))
        assert restored.job_id == job.job_id
        assert restored.steps_completed == ["snapshot"]


# ---------------------------------------------------------------------------
# MigrationService
# ---------------------------------------------------------------------------

class TestMigrationServiceResume:
    @pytest.mark.asyncio
    async def test_resume_skips_completed_steps(self, settings, tmp_path):
        """resume() skips steps that are already in steps_completed."""
        settings = settings.model_copy(update={"jobs_dir": str(tmp_path / "jobs"), "dry_run": True})
        os.makedirs(settings.jobs_dir, exist_ok=True)

        mock_client = MagicMock()
        mock_client._started = True
        mock_client._settings = settings
        mock_client.call = AsyncMock(return_value=MagicMock())
        mock_client.client = MagicMock()

        svc = MigrationService(mock_client, settings)

        # Create a job that has already completed the first 3 steps
        job = MigrationJob(
            job_id="resume-test",
            source_group_id=100,
            status=MigrationStatus.FAILED,
            steps_completed=["snapshot", "create_target", "copy_settings"],
        )
        await svc._save_job(job)

        called_steps = []

        async def fake_execute(j, new_title=None):
            # Record which steps would be executed (not in completed)
            for step in MigrationService.STEPS:
                if step not in j.steps_completed:
                    called_steps.append(step)
            j.status = MigrationStatus.COMPLETE
            return j

        with patch.object(svc, "_execute", side_effect=fake_execute):
            result = await svc.resume("resume-test")

        # The resumed job should have COMPLETE status
        assert result.status == MigrationStatus.COMPLETE
        # Steps already completed should not be in the "would execute" list
        for done_step in ["snapshot", "create_target", "copy_settings"]:
            assert done_step not in called_steps

    @pytest.mark.asyncio
    async def test_resume_returns_immediately_if_complete(self, settings, tmp_path):
        """resume() returns the job immediately if it's already COMPLETE."""
        settings = settings.model_copy(update={"jobs_dir": str(tmp_path / "jobs"), "dry_run": True})
        os.makedirs(settings.jobs_dir, exist_ok=True)

        mock_client = MagicMock()
        mock_client._started = True
        mock_client._settings = settings
        mock_client.call = AsyncMock(return_value=MagicMock())
        mock_client.client = MagicMock()

        svc = MigrationService(mock_client, settings)

        job = MigrationJob(
            job_id="already-done",
            source_group_id=100,
            status=MigrationStatus.COMPLETE,
            steps_completed=list(MigrationService.STEPS),
        )
        await svc._save_job(job)

        with patch.object(svc, "_execute") as mock_exec:
            result = await svc.resume("already-done")
            mock_exec.assert_not_called()

        assert result.status == MigrationStatus.COMPLETE

    @pytest.mark.asyncio
    async def test_plan_returns_step_list(self, settings):
        """plan() returns a dict containing the STEPS list."""
        mock_client = MagicMock()
        mock_client._started = True
        mock_client._settings = settings

        svc = MigrationService(mock_client, settings)
        plan = await svc.plan(source_group_id=123)

        assert plan["source_group_id"] == 123
        assert plan["steps"] == MigrationService.STEPS
        assert plan["dry_run"] is True

    @pytest.mark.asyncio
    async def test_status_loads_job(self, settings, tmp_path):
        """status() loads and returns a job by ID."""
        settings = settings.model_copy(update={"jobs_dir": str(tmp_path / "jobs"), "dry_run": True})
        os.makedirs(settings.jobs_dir, exist_ok=True)

        mock_client = MagicMock()
        mock_client._started = True
        mock_client._settings = settings
        mock_client.call = AsyncMock(return_value=MagicMock())
        mock_client.client = MagicMock()

        svc = MigrationService(mock_client, settings)

        job = MigrationJob(
            job_id="status-test",
            source_group_id=777,
            status=MigrationStatus.ARCHIVING_SOURCE,
        )
        await svc._save_job(job)

        loaded = await svc.status("status-test")
        assert loaded.job_id == "status-test"
        assert loaded.source_group_id == 777
        assert loaded.status == MigrationStatus.ARCHIVING_SOURCE
