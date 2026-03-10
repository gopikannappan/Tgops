"""Tests for tgops.core.config."""

from __future__ import annotations

import os

import pytest
from pydantic import ValidationError

from tgops.core.config import Settings


class TestSettings:
    def test_loads_from_kwargs(self):
        """Settings can be constructed with explicit values."""
        s = Settings(api_id=999, api_hash="abc", phone="+1111111111")
        assert s.api_id == 999
        assert s.api_hash == "abc"
        assert s.phone == "+1111111111"

    def test_default_dry_run_is_false(self):
        """dry_run defaults to False."""
        s = Settings(api_id=1, api_hash="h", phone="+1")
        assert s.dry_run is False

    def test_dry_run_can_be_overridden(self):
        """dry_run can be set to True."""
        s = Settings(api_id=1, api_hash="h", phone="+1", dry_run=True)
        assert s.dry_run is True

    def test_missing_api_id_raises(self):
        """Missing required api_id raises ValidationError."""
        with pytest.raises((ValidationError, Exception)):
            Settings(api_hash="h", phone="+1")  # type: ignore[call-arg]

    def test_missing_api_hash_raises(self):
        """Missing required api_hash raises ValidationError."""
        with pytest.raises((ValidationError, Exception)):
            Settings(api_id=1, phone="+1")  # type: ignore[call-arg]

    def test_missing_phone_raises(self):
        """Missing required phone raises ValidationError."""
        with pytest.raises((ValidationError, Exception)):
            Settings(api_id=1, api_hash="h")  # type: ignore[call-arg]

    def test_default_session_path_expanded(self):
        """session_path ~ is expanded to absolute path."""
        s = Settings(api_id=1, api_hash="h", phone="+1")
        assert not s.session_path.startswith("~")
        assert os.path.isabs(s.session_path)

    def test_default_audit_log_path_expanded(self):
        """audit_log_path ~ is expanded."""
        s = Settings(api_id=1, api_hash="h", phone="+1")
        assert not s.audit_log_path.startswith("~")

    def test_default_jobs_dir_expanded(self):
        """jobs_dir ~ is expanded."""
        s = Settings(api_id=1, api_hash="h", phone="+1")
        assert not s.jobs_dir.startswith("~")

    def test_base_delay_default(self):
        """base_delay_seconds defaults to 2.5."""
        s = Settings(api_id=1, api_hash="h", phone="+1")
        assert s.base_delay_seconds == 2.5

    def test_max_flood_retries_default(self):
        """max_flood_retries defaults to 3."""
        s = Settings(api_id=1, api_hash="h", phone="+1")
        assert s.max_flood_retries == 3

    def test_webhook_url_default_empty(self):
        """webhook_url defaults to empty string."""
        s = Settings(api_id=1, api_hash="h", phone="+1")
        assert s.webhook_url == ""

    def test_archive_prefix_default(self):
        """archive_prefix defaults to '[ARCHIVED]'."""
        s = Settings(api_id=1, api_hash="h", phone="+1")
        assert s.archive_prefix == "[ARCHIVED]"

    def test_loads_from_env_vars(self, monkeypatch):
        """Settings can be loaded from environment variables."""
        monkeypatch.setenv("TGOPS_API_ID", "42")
        monkeypatch.setenv("TGOPS_API_HASH", "env_hash")
        monkeypatch.setenv("TGOPS_PHONE", "+9999999999")
        monkeypatch.setenv("TGOPS_DRY_RUN", "true")

        s = Settings()
        assert s.api_id == 42
        assert s.api_hash == "env_hash"
        assert s.phone == "+9999999999"
        assert s.dry_run is True
