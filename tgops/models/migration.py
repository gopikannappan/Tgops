"""Migration job model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class MigrationStatus(str, Enum):
    PENDING = "PENDING"
    CREATING_TARGET = "CREATING_TARGET"
    TRANSFERRING_OWNERSHIP = "TRANSFERRING_OWNERSHIP"
    ARCHIVING_SOURCE = "ARCHIVING_SOURCE"
    BLASTING_INVITE = "BLASTING_INVITE"
    SETTING_REDIRECT = "SETTING_REDIRECT"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


@dataclass
class MigrationJob:
    """Tracks the state of a group migration."""

    job_id: str
    source_group_id: int
    target_group_id: int | None = None
    status: MigrationStatus = MigrationStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    error: str | None = None
    steps_completed: list[str] = field(default_factory=list)
