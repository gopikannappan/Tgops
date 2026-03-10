"""Group state model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class GroupState:
    """Snapshot of a Telegram group at a point in time."""

    group_id: int
    title: str
    username: str | None
    owner_user_id: int
    member_count: int
    invite_link: str | None
    is_archived: bool = False
    archived_at: datetime | None = None
    new_group_id: int | None = None
    snapshot_at: datetime = field(default_factory=datetime.utcnow)
