"""Member and offboarding models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


@dataclass
class MemberRecord:
    """A user's membership state across managed groups."""

    user_id: int
    username: str | None
    first_name: str
    last_name: str | None
    groups: list[int] = field(default_factory=list)
    is_active: dict[int, bool] = field(default_factory=dict)
    is_admin: dict[int, bool] = field(default_factory=dict)
    found_at: datetime = field(default_factory=datetime.utcnow)


class OffboardingMode(str, Enum):
    PLANNED = "PLANNED"
    EMERGENCY = "EMERGENCY"


@dataclass
class OffboardingJob:
    """Tracks the progress of a member offboarding operation."""

    job_id: str
    user_id: int
    username: str | None
    mode: OffboardingMode
    groups_found: list[int] = field(default_factory=list)
    groups_removed: list[int] = field(default_factory=list)
    groups_skipped: list[int] = field(default_factory=list)
    groups_failed: list[int] = field(default_factory=list)
    notify_message: str | None = None
    status: str = "PENDING"
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
